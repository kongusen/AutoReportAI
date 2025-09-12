"""
Progress Aggregator
==================

Coordinates progress reporting from multiple parallel agents.
Inspired by Claude Code's progress aggregation and ANR detection patterns.
"""

import asyncio
import logging
import uuid
import weakref
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, AsyncGenerator, Any, Callable, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
import json
import threading
from collections import defaultdict, deque

from .message_types import AgentMessage, MessageType, MessagePriority

logger = logging.getLogger(__name__)


class ProgressState(Enum):
    """Agent progress states"""
    NOT_STARTED = "not_started"
    INITIALIZING = "initializing" 
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class AggregationStrategy(Enum):
    """Progress aggregation strategies"""
    SIMPLE_AVERAGE = "simple_average"      # Simple average of all progress values
    WEIGHTED_AVERAGE = "weighted_average"  # Weighted by task importance
    MIN_PROGRESS = "min_progress"          # Minimum progress (conservative)
    MAX_PROGRESS = "max_progress"          # Maximum progress (optimistic) 
    COMPLETION_BASED = "completion_based"  # Based on completed vs total tasks


@dataclass
class AgentProgress:
    """Individual agent progress tracking"""
    agent_id: str
    task_id: str
    state: ProgressState = ProgressState.NOT_STARTED
    progress: float = 0.0  # 0.0 - 1.0
    
    # Detailed progress info
    current_step: Optional[str] = None
    step_index: int = 0
    total_steps: int = 1
    
    # Performance metrics
    started_at: Optional[datetime] = None
    last_update: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    
    # Quality metrics
    confidence: float = 1.0
    error_count: int = 0
    retry_count: int = 0
    
    # Resource usage
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    
    # Custom metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def update_progress(self, progress: float, step: str = None, metadata: Dict[str, Any] = None):
        """Update progress information"""
        self.progress = max(0.0, min(1.0, progress))  # Clamp to [0, 1]
        self.last_update = datetime.now(timezone.utc)
        
        if step:
            self.current_step = step
            
        if metadata:
            self.metadata.update(metadata)
        
        # Update state based on progress
        if self.progress == 0.0 and self.state == ProgressState.NOT_STARTED:
            self.state = ProgressState.INITIALIZING
        elif self.progress > 0.0 and self.progress < 1.0:
            self.state = ProgressState.RUNNING
        elif self.progress >= 1.0:
            self.state = ProgressState.COMPLETED
    
    def mark_failed(self, error: str):
        """Mark agent as failed"""
        self.state = ProgressState.FAILED
        self.error_count += 1
        self.metadata['last_error'] = error
        self.metadata['failed_at'] = datetime.now(timezone.utc).isoformat()
    
    def estimate_completion_time(self) -> Optional[datetime]:
        """Estimate completion time based on current progress"""
        if not self.started_at or self.progress <= 0:
            return None
        
        elapsed = datetime.now(timezone.utc) - self.started_at
        if self.progress > 0:
            total_estimated = elapsed / self.progress
            remaining = total_estimated - elapsed
            return datetime.now(timezone.utc) + remaining
        
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'agent_id': self.agent_id,
            'task_id': self.task_id,
            'state': self.state.value,
            'progress': self.progress,
            'current_step': self.current_step,
            'step_index': self.step_index,
            'total_steps': self.total_steps,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'estimated_completion': self.estimated_completion.isoformat() if self.estimated_completion else None,
            'confidence': self.confidence,
            'error_count': self.error_count,
            'retry_count': self.retry_count,
            'memory_usage_mb': self.memory_usage_mb,
            'cpu_usage_percent': self.cpu_usage_percent,
            'metadata': self.metadata
        }


@dataclass
class AggregatedProgress:
    """Aggregated progress from multiple agents"""
    aggregation_id: str
    overall_progress: float = 0.0
    overall_state: ProgressState = ProgressState.NOT_STARTED
    
    # Agent breakdown
    agent_progresses: Dict[str, AgentProgress] = field(default_factory=dict)
    total_agents: int = 0
    active_agents: int = 0
    completed_agents: int = 0
    failed_agents: int = 0
    
    # Timing
    started_at: Optional[datetime] = None
    last_update: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    estimated_completion: Optional[datetime] = None
    
    # Performance
    aggregation_strategy: AggregationStrategy = AggregationStrategy.WEIGHTED_AVERAGE
    throughput: Optional[float] = None  # tasks per second
    
    # Quality
    overall_confidence: float = 1.0
    total_errors: int = 0
    
    # Visualization data
    progress_history: List[Tuple[datetime, float]] = field(default_factory=list)
    error_timeline: List[Tuple[datetime, str, str]] = field(default_factory=list)  # (time, agent, error)
    
    def add_progress_history_point(self):
        """Add current progress to history for visualization"""
        self.progress_history.append((datetime.now(timezone.utc), self.overall_progress))
        
        # Limit history size
        if len(self.progress_history) > 1000:
            self.progress_history = self.progress_history[-1000:]
    
    def create_visualization(self) -> Dict[str, Any]:
        """Create progress visualization data"""
        agent_bars = []
        for agent_id, progress in self.agent_progresses.items():
            bar_length = 20
            filled = int(progress.progress * bar_length)
            bar = '█' * filled + '░' * (bar_length - filled)
            
            agent_bars.append({
                'agent_id': agent_id,
                'bar': bar,
                'percentage': progress.progress * 100,
                'state': progress.state.value,
                'current_step': progress.current_step,
                'eta': progress.estimate_completion_time().isoformat() if progress.estimate_completion_time() else None
            })
        
        return {
            'type': 'progress_bars',
            'overall_progress': self.overall_progress * 100,
            'agent_bars': agent_bars,
            'summary': f"{self.completed_agents}/{self.total_agents} completed",
            'errors': self.total_errors,
            'throughput': f"{self.throughput:.2f} tasks/sec" if self.throughput else "N/A"
        }


class ANRDetector:
    """
    Application Not Responding detector - inspired by Claude Code's ANR detection
    Monitors agent responsiveness and detects hanging operations
    """
    
    def __init__(self, threshold_seconds: int = 60):
        self.threshold_seconds = threshold_seconds
        self.monitored_agents: Dict[str, datetime] = {}
        self.alert_callbacks: List[Callable[[str, float], None]] = []
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ANR-Monitor")
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
    
    def start_monitoring(self, agent_id: str):
        """Start monitoring an agent"""
        self.monitored_agents[agent_id] = datetime.now(timezone.utc)
        
        if not self._monitoring:
            self._start_monitor_task()
    
    def stop_monitoring(self, agent_id: str):
        """Stop monitoring an agent"""
        self.monitored_agents.pop(agent_id, None)
        
        if not self.monitored_agents and self._monitoring:
            self._stop_monitor_task()
    
    def heartbeat(self, agent_id: str):
        """Record heartbeat from agent"""
        if agent_id in self.monitored_agents:
            self.monitored_agents[agent_id] = datetime.now(timezone.utc)
    
    def add_alert_callback(self, callback: Callable[[str, float], None]):
        """Add callback for ANR alerts"""
        self.alert_callbacks.append(callback)
    
    def _start_monitor_task(self):
        """Start the monitoring task"""
        if not self._monitoring:
            self._monitoring = True
            self._monitor_task = asyncio.create_task(self._monitor_loop())
    
    def _stop_monitor_task(self):
        """Stop the monitoring task"""
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
    
    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self._monitoring:
            try:
                current_time = datetime.now(timezone.utc)
                
                for agent_id, last_heartbeat in list(self.monitored_agents.items()):
                    time_since_heartbeat = (current_time - last_heartbeat).total_seconds()
                    
                    if time_since_heartbeat > self.threshold_seconds:
                        logger.warning(f"ANR detected: {agent_id} unresponsive for {time_since_heartbeat:.1f}s")
                        
                        # Notify callbacks
                        for callback in self.alert_callbacks:
                            try:
                                callback(agent_id, time_since_heartbeat)
                            except Exception as e:
                                logger.error(f"ANR callback error: {e}")
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"ANR monitor error: {e}")
                await asyncio.sleep(5)


class ProgressAggregator:
    """
    Central progress aggregation system
    Coordinates progress from multiple parallel agents with intelligent aggregation strategies
    """
    
    def __init__(self, aggregation_strategy: AggregationStrategy = AggregationStrategy.WEIGHTED_AVERAGE):
        self.aggregation_strategy = aggregation_strategy
        self.aggregations: Dict[str, AggregatedProgress] = {}
        self.agent_weights: Dict[str, float] = {}  # For weighted aggregation
        self.subscribers: List[Callable[[AggregatedProgress], None]] = []
        
        # ANR Detection
        self.anr_detector = ANRDetector()
        self.anr_detector.add_alert_callback(self._handle_anr_alert)
        
        # Performance tracking
        self.update_count = 0
        self.total_update_time = 0.0
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()
        
        logger.info(f"ProgressAggregator initialized with strategy: {aggregation_strategy.value}")
    
    def create_aggregation(self, aggregation_id: str, agent_ids: List[str], weights: Dict[str, float] = None) -> AggregatedProgress:
        """Create a new progress aggregation"""
        
        with self._lock:
            if aggregation_id in self.aggregations:
                raise ValueError(f"Aggregation {aggregation_id} already exists")
            
            aggregation = AggregatedProgress(
                aggregation_id=aggregation_id,
                total_agents=len(agent_ids),
                started_at=datetime.now(timezone.utc),
                aggregation_strategy=self.aggregation_strategy
            )
            
            # Initialize agent progress tracking
            for agent_id in agent_ids:
                progress = AgentProgress(
                    agent_id=agent_id,
                    task_id=aggregation_id,
                    started_at=datetime.now(timezone.utc)
                )
                aggregation.agent_progresses[agent_id] = progress
                
                # Set weights for weighted aggregation
                if weights and agent_id in weights:
                    self.agent_weights[agent_id] = weights[agent_id]
                else:
                    self.agent_weights[agent_id] = 1.0
                
                # Start ANR monitoring
                self.anr_detector.start_monitoring(agent_id)
            
            self.aggregations[aggregation_id] = aggregation
            logger.info(f"Created aggregation {aggregation_id} with {len(agent_ids)} agents")
            
            return aggregation
    
    def update_agent_progress(self, aggregation_id: str, agent_id: str, progress: float, 
                            step: str = None, metadata: Dict[str, Any] = None) -> Optional[AggregatedProgress]:
        """Update progress for a specific agent"""
        
        start_time = datetime.now(timezone.utc)
        
        with self._lock:
            if aggregation_id not in self.aggregations:
                logger.warning(f"Unknown aggregation: {aggregation_id}")
                return None
            
            aggregation = self.aggregations[aggregation_id]
            
            if agent_id not in aggregation.agent_progresses:
                logger.warning(f"Unknown agent {agent_id} in aggregation {aggregation_id}")
                return None
            
            # Update agent progress
            agent_progress = aggregation.agent_progresses[agent_id]
            agent_progress.update_progress(progress, step, metadata)
            
            # Record heartbeat for ANR detection
            self.anr_detector.heartbeat(agent_id)
            
            # Recalculate aggregated progress
            self._recalculate_aggregation(aggregation)
            
            # Notify subscribers
            self._notify_subscribers(aggregation)
            
            # Update performance metrics
            update_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            self.update_count += 1
            self.total_update_time += update_time
            
            logger.debug(f"Updated {agent_id} progress to {progress:.2%} in aggregation {aggregation_id}")
            
            return aggregation
    
    def mark_agent_failed(self, aggregation_id: str, agent_id: str, error: str) -> Optional[AggregatedProgress]:
        """Mark an agent as failed"""
        
        with self._lock:
            if aggregation_id not in self.aggregations:
                return None
            
            aggregation = self.aggregations[aggregation_id]
            
            if agent_id not in aggregation.agent_progresses:
                return None
            
            agent_progress = aggregation.agent_progresses[agent_id]
            agent_progress.mark_failed(error)
            
            # Add to error timeline
            aggregation.error_timeline.append((datetime.now(timezone.utc), agent_id, error))
            
            # Stop ANR monitoring for failed agent
            self.anr_detector.stop_monitoring(agent_id)
            
            # Recalculate aggregation
            self._recalculate_aggregation(aggregation)
            
            # Notify subscribers
            self._notify_subscribers(aggregation)
            
            logger.warning(f"Agent {agent_id} failed in aggregation {aggregation_id}: {error}")
            
            return aggregation
    
    def complete_aggregation(self, aggregation_id: str) -> Optional[AggregatedProgress]:
        """Mark aggregation as complete"""
        
        with self._lock:
            if aggregation_id not in self.aggregations:
                return None
            
            aggregation = self.aggregations[aggregation_id]
            aggregation.overall_state = ProgressState.COMPLETED
            aggregation.overall_progress = 1.0
            
            # Stop monitoring all agents
            for agent_id in aggregation.agent_progresses.keys():
                self.anr_detector.stop_monitoring(agent_id)
            
            # Final notification
            self._notify_subscribers(aggregation)
            
            logger.info(f"Aggregation {aggregation_id} completed")
            
            return aggregation
    
    def _recalculate_aggregation(self, aggregation: AggregatedProgress):
        """Recalculate overall progress based on strategy"""
        
        agent_progresses = list(aggregation.agent_progresses.values())
        
        if not agent_progresses:
            return
        
        # Update counts
        aggregation.active_agents = sum(1 for p in agent_progresses if p.state == ProgressState.RUNNING)
        aggregation.completed_agents = sum(1 for p in agent_progresses if p.state == ProgressState.COMPLETED)
        aggregation.failed_agents = sum(1 for p in agent_progresses if p.state == ProgressState.FAILED)
        aggregation.total_errors = sum(p.error_count for p in agent_progresses)
        
        # Calculate overall progress based on strategy
        if self.aggregation_strategy == AggregationStrategy.SIMPLE_AVERAGE:
            aggregation.overall_progress = sum(p.progress for p in agent_progresses) / len(agent_progresses)
            
        elif self.aggregation_strategy == AggregationStrategy.WEIGHTED_AVERAGE:
            total_weight = 0.0
            weighted_sum = 0.0
            
            for progress in agent_progresses:
                weight = self.agent_weights.get(progress.agent_id, 1.0)
                weighted_sum += progress.progress * weight
                total_weight += weight
            
            aggregation.overall_progress = weighted_sum / max(total_weight, 1.0)
            
        elif self.aggregation_strategy == AggregationStrategy.MIN_PROGRESS:
            aggregation.overall_progress = min(p.progress for p in agent_progresses)
            
        elif self.aggregation_strategy == AggregationStrategy.MAX_PROGRESS:
            aggregation.overall_progress = max(p.progress for p in agent_progresses)
            
        elif self.aggregation_strategy == AggregationStrategy.COMPLETION_BASED:
            aggregation.overall_progress = aggregation.completed_agents / max(aggregation.total_agents, 1)
        
        # Update overall state
        if aggregation.failed_agents == aggregation.total_agents:
            aggregation.overall_state = ProgressState.FAILED
        elif aggregation.completed_agents == aggregation.total_agents:
            aggregation.overall_state = ProgressState.COMPLETED
        elif aggregation.active_agents > 0:
            aggregation.overall_state = ProgressState.RUNNING
        else:
            aggregation.overall_state = ProgressState.WAITING
        
        # Calculate overall confidence
        confidences = [p.confidence for p in agent_progresses if p.confidence is not None]
        if confidences:
            aggregation.overall_confidence = sum(confidences) / len(confidences)
        
        # Estimate completion time
        running_agents = [p for p in agent_progresses if p.state == ProgressState.RUNNING]
        if running_agents:
            estimates = [p.estimate_completion_time() for p in running_agents]
            valid_estimates = [e for e in estimates if e is not None]
            if valid_estimates:
                aggregation.estimated_completion = max(valid_estimates)  # Latest completion
        
        # Calculate throughput
        if aggregation.started_at:
            elapsed = (datetime.now(timezone.utc) - aggregation.started_at).total_seconds()
            if elapsed > 0:
                aggregation.throughput = aggregation.completed_agents / elapsed
        
        # Add to progress history
        aggregation.add_progress_history_point()
        aggregation.last_update = datetime.now(timezone.utc)
    
    def _notify_subscribers(self, aggregation: AggregatedProgress):
        """Notify all subscribers of progress update"""
        for subscriber in self.subscribers:
            try:
                subscriber(aggregation)
            except Exception as e:
                logger.error(f"Subscriber notification error: {e}")
    
    def _handle_anr_alert(self, agent_id: str, unresponsive_time: float):
        """Handle ANR alert from detector"""
        
        # Find aggregations containing this agent
        affected_aggregations = []
        
        with self._lock:
            for aggregation_id, aggregation in self.aggregations.items():
                if agent_id in aggregation.agent_progresses:
                    affected_aggregations.append((aggregation_id, aggregation))
        
        # Mark agent as timeout in affected aggregations
        for aggregation_id, aggregation in affected_aggregations:
            agent_progress = aggregation.agent_progresses[agent_id]
            agent_progress.state = ProgressState.TIMEOUT
            agent_progress.metadata['anr_time'] = unresponsive_time
            
            # Add to error timeline
            aggregation.error_timeline.append((
                datetime.now(timezone.utc), 
                agent_id, 
                f"ANR detected - unresponsive for {unresponsive_time:.1f}s"
            ))
            
            self._recalculate_aggregation(aggregation)
            self._notify_subscribers(aggregation)
    
    def subscribe(self, callback: Callable[[AggregatedProgress], None]):
        """Subscribe to progress updates"""
        self.subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable[[AggregatedProgress], None]):
        """Unsubscribe from progress updates"""
        if callback in self.subscribers:
            self.subscribers.remove(callback)
    
    def get_aggregation(self, aggregation_id: str) -> Optional[AggregatedProgress]:
        """Get aggregation by ID"""
        with self._lock:
            return self.aggregations.get(aggregation_id)
    
    def list_aggregations(self) -> List[str]:
        """List all aggregation IDs"""
        with self._lock:
            return list(self.aggregations.keys())
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get aggregator performance metrics"""
        avg_update_time = self.total_update_time / max(self.update_count, 1)
        
        return {
            'total_updates': self.update_count,
            'average_update_time_ms': avg_update_time,
            'active_aggregations': len(self.aggregations),
            'total_agents_monitored': sum(len(a.agent_progresses) for a in self.aggregations.values()),
            'anr_threshold_seconds': self.anr_detector.threshold_seconds,
            'monitored_agents': len(self.anr_detector.monitored_agents)
        }
    
    def _start_cleanup_task(self):
        """Start background cleanup task"""
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(300)  # Every 5 minutes
                    self._cleanup_old_aggregations()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Cleanup task error: {e}")
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())
    
    def _cleanup_old_aggregations(self):
        """Clean up old completed aggregations"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
        
        with self._lock:
            to_remove = []
            
            for aggregation_id, aggregation in self.aggregations.items():
                if (aggregation.overall_state in [ProgressState.COMPLETED, ProgressState.FAILED] and
                    aggregation.last_update < cutoff_time):
                    to_remove.append(aggregation_id)
            
            for aggregation_id in to_remove:
                del self.aggregations[aggregation_id]
                logger.debug(f"Cleaned up old aggregation: {aggregation_id}")
    
    def shutdown(self):
        """Shutdown the aggregator"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # Stop all ANR monitoring
        for agent_id in list(self.anr_detector.monitored_agents.keys()):
            self.anr_detector.stop_monitoring(agent_id)
        
        self.anr_detector.executor.shutdown(wait=True)
        
        logger.info("ProgressAggregator shutdown complete")


# Convenience functions

def create_simple_aggregator() -> ProgressAggregator:
    """Create aggregator with simple average strategy"""
    return ProgressAggregator(AggregationStrategy.SIMPLE_AVERAGE)

def create_weighted_aggregator() -> ProgressAggregator:
    """Create aggregator with weighted average strategy"""
    return ProgressAggregator(AggregationStrategy.WEIGHTED_AVERAGE)

async def aggregate_agent_stream(agents: List[str], 
                               progress_stream: AsyncGenerator[Tuple[str, float], None],
                               aggregator: ProgressAggregator = None) -> AsyncGenerator[AggregatedProgress, None]:
    """Convenience function to aggregate a stream of agent progress updates"""
    
    if aggregator is None:
        aggregator = create_simple_aggregator()
    
    aggregation_id = str(uuid.uuid4())
    aggregation = aggregator.create_aggregation(aggregation_id, agents)
    
    # Subscribe to updates
    update_queue = asyncio.Queue()
    
    def on_update(agg: AggregatedProgress):
        if agg.aggregation_id == aggregation_id:
            try:
                update_queue.put_nowait(agg)
            except asyncio.QueueFull:
                logger.warning("Update queue full, dropping update")
    
    aggregator.subscribe(on_update)
    
    try:
        # Start processing progress stream
        async def process_stream():
            async for agent_id, progress in progress_stream:
                aggregator.update_agent_progress(aggregation_id, agent_id, progress)
        
        stream_task = asyncio.create_task(process_stream())
        
        # Yield updates
        while not stream_task.done():
            try:
                update = await asyncio.wait_for(update_queue.get(), timeout=1.0)
                yield update
                
                if update.overall_state in [ProgressState.COMPLETED, ProgressState.FAILED]:
                    break
                    
            except asyncio.TimeoutError:
                continue
    
    finally:
        aggregator.unsubscribe(on_update)


__all__ = [
    "ProgressState",
    "AggregationStrategy", 
    "AgentProgress",
    "AggregatedProgress",
    "ANRDetector",
    "ProgressAggregator",
    "create_simple_aggregator",
    "create_weighted_aggregator",
    "aggregate_agent_stream",
]