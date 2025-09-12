"""
Streaming Message Parser
========================

Advanced streaming parser for handling partial agent messages and communication.
Inspired by Claude Code's streaming JSON parser with enhanced agent-specific features.
"""

import json
import re
import logging
import asyncio
from typing import Any, Dict, List, Optional, Union, AsyncGenerator, Iterator, Tuple, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import weakref
from concurrent.futures import ThreadPoolExecutor

from .message_types import AgentMessage, MessageType, MessagePriority

logger = logging.getLogger(__name__)


class ParseState(Enum):
    """Parser state machine states"""
    WAITING_START = "waiting_start"
    PARSING_HEADER = "parsing_header" 
    PARSING_PAYLOAD = "parsing_payload"
    PARSING_METADATA = "parsing_metadata"
    VALIDATING = "validating"
    COMPLETED = "completed"
    ERROR_RECOVERY = "error_recovery"
    FAILED = "failed"


class ParseResult(Enum):
    """Parse result types"""
    PARTIAL = "partial"           # Partial message parsed
    COMPLETE = "complete"         # Complete message parsed
    INVALID = "invalid"           # Invalid data
    RECOVERED = "recovered"       # Recovered from error
    STREAMING = "streaming"       # Streaming chunk received


@dataclass
class ParserState:
    """Internal parser state tracking"""
    current_state: ParseState = ParseState.WAITING_START
    buffer_position: int = 0
    message_depth: int = 0
    in_string: bool = False
    escape_next: bool = False
    quote_char: Optional[str] = None
    bracket_stack: List[str] = field(default_factory=list)
    partial_data: Dict[str, Any] = field(default_factory=dict)
    error_count: int = 0
    recovery_attempts: int = 0
    
    def reset(self):
        """Reset parser state"""
        self.current_state = ParseState.WAITING_START
        self.buffer_position = 0
        self.message_depth = 0
        self.in_string = False
        self.escape_next = False
        self.quote_char = None
        self.bracket_stack.clear()
        self.partial_data.clear()
        self.error_count = 0
        self.recovery_attempts = 0


@dataclass
class ParsedMessage:
    """Result of message parsing"""
    result_type: ParseResult
    message: Optional[AgentMessage] = None
    partial_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    confidence: float = 1.0
    bytes_consumed: int = 0
    
    # Recovery information
    recovery_used: bool = False
    recovery_strategy: Optional[str] = None
    
    # Performance metrics
    parse_time_ms: Optional[float] = None
    buffer_size: int = 0
    
    # Quality metrics
    data_integrity: float = 1.0  # 0.0 - 1.0
    validation_passed: bool = True


class StreamingMessageParser:
    """
    Advanced streaming parser for agent messages
    
    Features:
    1. Incremental parsing of partial messages
    2. Error recovery with multiple strategies
    3. Message validation and quality assessment
    4. Performance monitoring and optimization
    5. Memory-efficient buffer management
    """
    
    def __init__(self, max_buffer_size: int = 1024 * 1024):  # 1MB default
        self.max_buffer_size = max_buffer_size
        self.buffer = ""
        self.state = ParserState()
        self.parse_history: List[Dict[str, Any]] = []
        self.max_history = 1000
        
        # Recovery strategies
        self.recovery_strategies = [
            self._recover_with_bracket_matching,
            self._recover_with_quote_fixing, 
            self._recover_with_field_extraction,
            self._recover_with_template_matching,
            self._recover_with_truncation
        ]
        
        # Validation rules
        self.validation_rules: List[Callable[[Dict[str, Any]], bool]] = [
            self._validate_required_fields,
            self._validate_message_type,
            self._validate_agent_ids,
            self._validate_payload_size
        ]
        
        # Performance tracking
        self.total_messages_parsed = 0
        self.total_parse_time = 0.0
        self.total_bytes_processed = 0
        
        # Memory management using weak references
        self._message_cache = weakref.WeakValueDictionary()
        self._cleanup_interval = 1000  # Clean up every 1000 parses
        
        logger.debug("StreamingMessageParser initialized")
    
    async def parse_stream(self, data_stream: AsyncGenerator[bytes, None]) -> AsyncGenerator[ParsedMessage, None]:
        """
        Parse streaming data and yield messages as they become available
        
        Args:
            data_stream: Async generator of byte chunks
            
        Yields:
            ParsedMessage: Parsed messages or partial results
        """
        
        chunk_count = 0
        start_time = datetime.utcnow()
        
        try:
            async for chunk in data_stream:
                chunk_count += 1
                
                # Convert bytes to string
                try:
                    chunk_str = chunk.decode('utf-8') if isinstance(chunk, bytes) else str(chunk)
                except UnicodeDecodeError as e:
                    yield ParsedMessage(
                        result_type=ParseResult.INVALID,
                        error=f"Unicode decode error: {e}",
                        confidence=0.0
                    )
                    continue
                
                # Add to buffer
                if len(self.buffer) + len(chunk_str) > self.max_buffer_size:
                    logger.warning("Buffer size limit reached, dropping oldest data")
                    self._compress_buffer()
                
                self.buffer += chunk_str
                self.total_bytes_processed += len(chunk_str)
                
                # Record parsing attempt
                self.parse_history.append({
                    "chunk": chunk_count,
                    "chunk_size": len(chunk_str),
                    "buffer_size": len(self.buffer),
                    "timestamp": datetime.utcnow().isoformat(),
                    "state": self.state.current_state.value
                })
                
                # Trim history if needed
                if len(self.parse_history) > self.max_history:
                    self.parse_history = self.parse_history[-self.max_history:]
                
                # Attempt to parse messages from current buffer
                async for message in self._parse_buffer():
                    yield message
                    
                # Periodic cleanup
                if chunk_count % self._cleanup_interval == 0:
                    self._perform_memory_cleanup()
                    
        except Exception as e:
            logger.error(f"Streaming parse error: {e}", exc_info=True)
            yield ParsedMessage(
                result_type=ParseResult.INVALID,
                error=f"Stream parsing failed: {e}",
                confidence=0.0
            )
        finally:
            # Final processing
            if self.buffer.strip():
                async for message in self._parse_buffer(final=True):
                    yield message
            
            # Log performance metrics
            total_time = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"Stream parsing completed: {chunk_count} chunks, "
                       f"{self.total_bytes_processed} bytes, {total_time:.2f}s")
    
    async def _parse_buffer(self, final: bool = False) -> AsyncGenerator[ParsedMessage, None]:
        """Parse current buffer content"""
        
        parse_start = datetime.utcnow()
        
        # Try multiple parsing approaches
        parsing_methods = [
            self._parse_complete_messages,
            self._parse_partial_messages,
            self._parse_with_recovery
        ]
        
        messages_found = False
        
        for method in parsing_methods:
            try:
                async for result in method():
                    messages_found = True
                    
                    # Calculate parse time
                    result.parse_time_ms = (datetime.utcnow() - parse_start).total_seconds() * 1000
                    result.buffer_size = len(self.buffer)
                    
                    # Update statistics
                    if result.result_type == ParseResult.COMPLETE:
                        self.total_messages_parsed += 1
                        self.total_parse_time += result.parse_time_ms
                    
                    yield result
                    
                    # Remove parsed data from buffer if complete
                    if result.result_type in [ParseResult.COMPLETE, ParseResult.RECOVERED]:
                        self.buffer = self.buffer[result.bytes_consumed:]
                        self.state.buffer_position = 0
                
                # If we found messages with this method, don't try other methods
                if messages_found:
                    break
                    
            except Exception as e:
                logger.debug(f"Parsing method {method.__name__} failed: {e}")
                continue
        
        # If this is the final parse and we have remaining data, try recovery
        if final and self.buffer.strip() and not messages_found:
            logger.warning("Final parse with remaining buffer data, attempting recovery")
            async for result in self._parse_with_recovery():
                yield result
    
    async def _parse_complete_messages(self) -> AsyncGenerator[ParsedMessage, None]:
        """Try to parse complete JSON messages from buffer"""
        
        # Look for complete message boundaries
        message_boundaries = self._find_message_boundaries()
        
        for start, end in message_boundaries:
            message_text = self.buffer[start:end]
            
            try:
                # Parse JSON
                message_data = json.loads(message_text)
                
                # Validate the message data
                validation_result = self._validate_message_data(message_data)
                
                if validation_result['valid']:
                    # Convert to AgentMessage
                    agent_message = self._dict_to_agent_message(message_data)
                    
                    yield ParsedMessage(
                        result_type=ParseResult.COMPLETE,
                        message=agent_message,
                        confidence=validation_result['confidence'],
                        bytes_consumed=end,
                        validation_passed=True,
                        data_integrity=validation_result['integrity']
                    )
                else:
                    logger.warning(f"Message validation failed: {validation_result['errors']}")
                    yield ParsedMessage(
                        result_type=ParseResult.INVALID,
                        error=f"Validation failed: {', '.join(validation_result['errors'])}",
                        bytes_consumed=end,
                        confidence=0.0,
                        validation_passed=False
                    )
                    
            except json.JSONDecodeError as e:
                logger.debug(f"JSON decode error: {e}")
                continue
    
    async def _parse_partial_messages(self) -> AsyncGenerator[ParsedMessage, None]:
        """Extract partial message data using pattern matching"""
        
        # Pattern-based field extraction
        field_patterns = {
            'message_id': r'"message_id":\s*"([^"]*)"',
            'message_type': r'"message_type":\s*"([^"]*)"',
            'from_agent': r'"from_agent":\s*"([^"]*)"',
            'to_agent': r'"to_agent":\s*"([^"]*)"',
            'priority': r'"priority":\s*"?(\w+)"?',
            'progress': r'"progress":\s*([\d.]+)',
            'payload': r'"payload":\s*({[^}]*}|\[[^\]]*\]|"[^"]*"|\d+|true|false|null)'
        }
        
        partial_data = {}
        confidence = 0.0
        fields_found = 0
        
        for field_name, pattern in field_patterns.items():
            match = re.search(pattern, self.buffer)
            if match:
                try:
                    value = match.group(1)
                    
                    # Type conversion
                    if field_name == 'progress':
                        value = float(value)
                    elif field_name == 'payload':
                        try:
                            value = json.loads(value)
                        except json.JSONDecodeError:
                            pass  # Keep as string
                    
                    partial_data[field_name] = value
                    fields_found += 1
                    
                except (ValueError, TypeError) as e:
                    logger.debug(f"Field conversion error for {field_name}: {e}")
                    continue
        
        if fields_found > 0:
            confidence = min(1.0, fields_found / len(field_patterns))
            
            yield ParsedMessage(
                result_type=ParseResult.PARTIAL,
                partial_data=partial_data,
                confidence=confidence,
                bytes_consumed=0,  # Don't consume buffer for partial parses
                data_integrity=confidence
            )
    
    async def _parse_with_recovery(self) -> AsyncGenerator[ParsedMessage, None]:
        """Attempt recovery parsing using various strategies"""
        
        if self.state.recovery_attempts >= len(self.recovery_strategies):
            logger.error("All recovery strategies exhausted")
            return
        
        logger.info(f"Attempting recovery parse (attempt {self.state.recovery_attempts + 1})")
        
        for i, strategy in enumerate(self.recovery_strategies[self.state.recovery_attempts:]):
            try:
                recovered_data = await strategy()
                
                if recovered_data:
                    try:
                        # Try to parse recovered data
                        message_data = json.loads(recovered_data)
                        validation_result = self._validate_message_data(message_data)
                        
                        if validation_result['valid']:
                            agent_message = self._dict_to_agent_message(message_data)
                            
                            yield ParsedMessage(
                                result_type=ParseResult.RECOVERED,
                                message=agent_message,
                                confidence=validation_result['confidence'] * 0.8,  # Lower confidence for recovered
                                bytes_consumed=len(self.buffer),  # Consume entire buffer
                                recovery_used=True,
                                recovery_strategy=strategy.__name__,
                                validation_passed=True,
                                data_integrity=validation_result['integrity'] * 0.8
                            )
                            
                            self.state.recovery_attempts = 0  # Reset on success
                            return
                            
                    except json.JSONDecodeError:
                        continue
                        
            except Exception as e:
                logger.debug(f"Recovery strategy {strategy.__name__} failed: {e}")
                continue
        
        self.state.recovery_attempts += 1
        
        # If all recovery failed
        yield ParsedMessage(
            result_type=ParseResult.INVALID,
            error="All recovery strategies failed",
            confidence=0.0,
            recovery_used=True,
            validation_passed=False
        )
    
    def _find_message_boundaries(self) -> List[Tuple[int, int]]:
        """Find complete message boundaries in buffer"""
        boundaries = []
        
        # Look for JSON object boundaries
        i = 0
        while i < len(self.buffer):
            if self.buffer[i] == '{':
                # Found potential start, find matching end
                bracket_count = 1
                start = i
                
                j = i + 1
                while j < len(self.buffer) and bracket_count > 0:
                    char = self.buffer[j]
                    
                    if char == '{':
                        bracket_count += 1
                    elif char == '}':
                        bracket_count -= 1
                    
                    j += 1
                
                if bracket_count == 0:
                    # Found complete message
                    boundaries.append((start, j))
                    i = j
                else:
                    # Incomplete message
                    break
            else:
                i += 1
        
        return boundaries
    
    def _validate_message_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parsed message data"""
        errors = []
        confidence = 1.0
        integrity = 1.0
        
        # Run all validation rules
        for rule in self.validation_rules:
            try:
                if not rule(data):
                    rule_name = rule.__name__.replace('_validate_', '')
                    errors.append(f"Failed {rule_name} validation")
                    confidence *= 0.8
                    integrity *= 0.9
            except Exception as e:
                errors.append(f"Validation error: {e}")
                confidence *= 0.7
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'confidence': max(0.0, confidence),
            'integrity': max(0.0, integrity)
        }
    
    def _validate_required_fields(self, data: Dict[str, Any]) -> bool:
        """Validate required message fields"""
        required_fields = ['message_type', 'from_agent', 'to_agent']
        return all(field in data and data[field] for field in required_fields)
    
    def _validate_message_type(self, data: Dict[str, Any]) -> bool:
        """Validate message type is valid"""
        msg_type = data.get('message_type')
        if not msg_type:
            return False
        
        try:
            MessageType(msg_type)
            return True
        except ValueError:
            return False
    
    def _validate_agent_ids(self, data: Dict[str, Any]) -> bool:
        """Validate agent IDs are reasonable"""
        from_agent = data.get('from_agent', '')
        to_agent = data.get('to_agent', '')
        
        # Basic validation - not empty and reasonable length
        return (len(from_agent) > 0 and len(from_agent) < 256 and 
                len(to_agent) > 0 and len(to_agent) < 256)
    
    def _validate_payload_size(self, data: Dict[str, Any]) -> bool:
        """Validate payload size is reasonable"""
        payload = data.get('payload')
        if payload is None:
            return True
        
        # Estimate payload size
        try:
            payload_size = len(json.dumps(payload))
            return payload_size < 10 * 1024 * 1024  # 10MB limit
        except:
            return True  # If we can't measure, assume valid
    
    def _dict_to_agent_message(self, data: Dict[str, Any]) -> AgentMessage:
        """Convert dictionary to AgentMessage"""
        try:
            return AgentMessage.from_dict(data)
        except Exception as e:
            logger.warning(f"Error converting dict to AgentMessage: {e}")
            # Create a basic message with available data
            return AgentMessage(
                message_type=MessageType(data.get('message_type', MessageType.MESSAGE_SEND.value)),
                from_agent=data.get('from_agent', ''),
                to_agent=data.get('to_agent', ''),
                payload=data.get('payload')
            )
    
    # Recovery strategies
    
    async def _recover_with_bracket_matching(self) -> Optional[str]:
        """Recover by fixing bracket mismatches"""
        open_count = self.buffer.count('{')
        close_count = self.buffer.count('}')
        
        if open_count > close_count:
            return self.buffer + '}' * (open_count - close_count)
        elif close_count > open_count:
            # Remove extra closing brackets from end
            result = self.buffer
            for _ in range(close_count - open_count):
                result = result.rsplit('}', 1)[0] if '}' in result else result
            return result
        
        return None
    
    async def _recover_with_quote_fixing(self) -> Optional[str]:
        """Recover by fixing quote mismatches"""
        # Count unescaped quotes
        quote_count = 0
        i = 0
        while i < len(self.buffer):
            if self.buffer[i] == '"' and (i == 0 or self.buffer[i-1] != '\\'):
                quote_count += 1
            i += 1
        
        if quote_count % 2 == 1:
            return self.buffer + '"'
        
        return None
    
    async def _recover_with_field_extraction(self) -> Optional[str]:
        """Recover by extracting valid fields into a new message"""
        # Extract any valid-looking JSON fields
        field_pattern = r'"(\w+)":\s*("(?:[^"\\]|\\.)*"|[^,}\s]*)'
        matches = re.findall(field_pattern, self.buffer)
        
        if matches:
            recovered_obj = {}
            for key, value in matches:
                try:
                    # Try to parse the value
                    parsed_value = json.loads(value)
                    recovered_obj[key] = parsed_value
                except json.JSONDecodeError:
                    # Keep as string if JSON parsing fails
                    recovered_obj[key] = value.strip('"')
            
            if recovered_obj:
                return json.dumps(recovered_obj)
        
        return None
    
    async def _recover_with_template_matching(self) -> Optional[str]:
        """Recover using common message templates"""
        
        templates = {
            'basic_message': {
                'message_type': 'message_send',
                'from_agent': 'unknown',
                'to_agent': 'unknown',
                'payload': None
            },
            'task_request': {
                'message_type': 'task_request',
                'from_agent': 'system',
                'to_agent': 'agent',
                'payload': {},
                'priority': 'NORMAL'
            }
        }
        
        # Try to match buffer content to templates
        for template_name, template in templates.items():
            try:
                # Extract values for template fields
                recovered = template.copy()
                
                for field in template.keys():
                    pattern = rf'"{field}":\s*("(?:[^"\\]|\\.)*"|[^,}}\s]*)'
                    match = re.search(pattern, self.buffer)
                    if match:
                        value = match.group(1)
                        try:
                            recovered[field] = json.loads(value)
                        except json.JSONDecodeError:
                            recovered[field] = value.strip('"')
                
                return json.dumps(recovered)
                
            except Exception:
                continue
        
        return None
    
    async def _recover_with_truncation(self) -> Optional[str]:
        """Recover by truncating to last valid JSON"""
        
        # Try truncating from different positions
        for i in range(len(self.buffer) - 1, max(0, len(self.buffer) - 1000), -1):
            if self.buffer[i] in ['}', ']']:
                candidate = self.buffer[:i+1]
                try:
                    json.loads(candidate)
                    return candidate
                except json.JSONDecodeError:
                    continue
        
        return None
    
    def _compress_buffer(self):
        """Compress buffer when size limit is reached"""
        # Keep only the last 50% of buffer
        keep_size = self.max_buffer_size // 2
        self.buffer = self.buffer[-keep_size:]
        logger.debug(f"Buffer compressed to {len(self.buffer)} bytes")
    
    def _perform_memory_cleanup(self):
        """Perform periodic memory cleanup"""
        # Clear old parse history
        if len(self.parse_history) > self.max_history // 2:
            self.parse_history = self.parse_history[-self.max_history // 2:]
        
        # Reset state if too many errors
        if self.state.error_count > 10:
            logger.warning("High error count, resetting parser state")
            self.state.reset()
        
        logger.debug("Memory cleanup performed")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get parser performance metrics"""
        avg_parse_time = (self.total_parse_time / max(self.total_messages_parsed, 1))
        throughput = (self.total_bytes_processed / max(self.total_parse_time / 1000, 0.001))  # bytes per second
        
        return {
            'total_messages_parsed': self.total_messages_parsed,
            'total_bytes_processed': self.total_bytes_processed,
            'total_parse_time_ms': self.total_parse_time,
            'average_parse_time_ms': avg_parse_time,
            'throughput_bytes_per_sec': throughput,
            'buffer_size': len(self.buffer),
            'current_state': self.state.current_state.value,
            'error_count': self.state.error_count,
            'recovery_attempts': self.state.recovery_attempts,
            'cache_size': len(self._message_cache)
        }
    
    def reset(self):
        """Reset parser to initial state"""
        self.buffer = ""
        self.state.reset()
        self.parse_history.clear()
        self._message_cache.clear()
        logger.debug("Parser reset to initial state")


# Convenience functions

async def parse_message_stream(data_stream: AsyncGenerator[bytes, None]) -> AsyncGenerator[AgentMessage, None]:
    """Convenience function to parse a stream and yield only complete messages"""
    parser = StreamingMessageParser()
    
    async for result in parser.parse_stream(data_stream):
        if result.result_type in [ParseResult.COMPLETE, ParseResult.RECOVERED] and result.message:
            yield result.message

async def parse_single_message(data: Union[str, bytes, Dict[str, Any]]) -> Optional[AgentMessage]:
    """Parse a single message from various input types"""
    
    if isinstance(data, dict):
        try:
            return AgentMessage.from_dict(data)
        except Exception as e:
            logger.error(f"Error parsing dict to AgentMessage: {e}")
            return None
    
    if isinstance(data, bytes):
        try:
            data = data.decode('utf-8')
        except UnicodeDecodeError:
            logger.error("Unicode decode error")
            return None
    
    if isinstance(data, str):
        try:
            parsed_data = json.loads(data)
            return AgentMessage.from_dict(parsed_data)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return None
    
    return None


__all__ = [
    "ParseState",
    "ParseResult", 
    "ParserState",
    "ParsedMessage",
    "StreamingMessageParser",
    "parse_message_stream",
    "parse_single_message",
]