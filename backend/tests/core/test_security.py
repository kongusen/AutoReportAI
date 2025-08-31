"""
安全模块测试
"""

import pytest
from datetime import datetime, timedelta
from jose import jwt
from app.core.security import (
    create_access_token,
    verify_password,
    get_password_hash,
    decode_token
)
from app.core.config import settings


@pytest.mark.unit
class TestPasswordSecurity:
    """测试密码安全功能"""
    
    def test_password_hashing(self):
        """测试密码哈希"""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert len(hashed) > 50  # bcrypt哈希长度
        assert hashed.startswith("$2b$")
    
    def test_password_verification(self):
        """测试密码验证"""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
        assert verify_password(wrong_password, hashed) is False
    
    def test_different_passwords_different_hashes(self):
        """测试不同密码生成不同哈希"""
        password1 = "password1"
        password2 = "password2"
        
        hash1 = get_password_hash(password1)
        hash2 = get_password_hash(password2)
        
        assert hash1 != hash2
    
    def test_same_password_different_hashes(self):
        """测试相同密码生成不同哈希（salt作用）"""
        password = "testpassword123"
        
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # 由于salt的存在，相同密码会生成不同哈希
        assert hash1 != hash2
        # 但都能通过验证
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


@pytest.mark.unit
class TestTokenSecurity:
    """测试Token安全功能"""
    
    def test_access_token_creation(self):
        """测试访问token创建"""
        subject = "test_user_id"
        token = create_access_token(subject=subject)
        
        assert isinstance(token, str)
        assert len(token) > 50
        
        # 验证token结构
        parts = token.split(".")
        assert len(parts) == 3  # header.payload.signature
    
    def test_access_token_with_expiration(self):
        """测试带过期时间的token"""
        subject = "test_user_id"
        expires_delta = timedelta(minutes=30)
        token = create_access_token(subject=subject, expires_delta=expires_delta)
        
        # 解码验证
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        assert payload["sub"] == subject
        
        # 验证过期时间
        exp_timestamp = payload["exp"]
        exp_datetime = datetime.fromtimestamp(exp_timestamp)
        expected_exp = datetime.utcnow() + expires_delta
        
        # 允许1分钟的时间误差
        assert abs((exp_datetime - expected_exp).total_seconds()) < 60
    
    def test_token_decode_success(self):
        """测试token解码成功"""
        subject = "test_user_id"
        token = create_access_token(subject=subject)
        
        decoded_subject = decode_token(token)
        assert decoded_subject == subject
    
    def test_token_decode_invalid_token(self):
        """测试无效token解码"""
        invalid_token = "invalid.token.here"
        
        decoded_subject = decode_token(invalid_token)
        assert decoded_subject is None
    
    def test_token_decode_expired_token(self):
        """测试过期token解码"""
        subject = "test_user_id"
        expires_delta = timedelta(seconds=-1)  # 已过期
        token = create_access_token(subject=subject, expires_delta=expires_delta)
        
        # 等待确保token过期
        import time
        time.sleep(1)
        
        decoded_subject = decode_token(token)
        assert decoded_subject is None
    
    def test_token_decode_tampered_token(self):
        """测试篡改token解码"""
        subject = "test_user_id"
        token = create_access_token(subject=subject)
        
        # 篡改token
        parts = token.split(".")
        tampered_token = parts[0] + ".tampered." + parts[2]
        
        decoded_subject = decode_token(tampered_token)
        assert decoded_subject is None
    
    def test_token_contains_correct_claims(self):
        """测试token包含正确的claims"""
        subject = "test_user_id"
        token = create_access_token(subject=subject)
        
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        
        assert "sub" in payload
        assert "exp" in payload
        assert payload["sub"] == subject
        
        # 验证过期时间是未来时间
        exp_timestamp = payload["exp"]
        assert exp_timestamp > datetime.utcnow().timestamp()


@pytest.mark.integration
class TestSecurityIntegration:
    """测试安全功能集成"""
    
    def test_full_password_workflow(self):
        """测试完整密码工作流"""
        original_password = "my_secure_password_123"
        
        # 1. 哈希密码
        hashed = get_password_hash(original_password)
        
        # 2. 验证正确密码
        assert verify_password(original_password, hashed) is True
        
        # 3. 验证错误密码
        assert verify_password("wrong_password", hashed) is False
    
    def test_full_token_workflow(self):
        """测试完整token工作流"""
        user_id = "user_12345"
        
        # 1. 创建token
        token = create_access_token(subject=user_id)
        
        # 2. 解码token
        decoded_id = decode_token(token)
        
        # 3. 验证结果
        assert decoded_id == user_id
    
    def test_token_expiration_workflow(self):
        """测试token过期工作流"""
        user_id = "user_12345"
        
        # 创建立即过期的token
        token = create_access_token(
            subject=user_id, 
            expires_delta=timedelta(seconds=1)
        )
        
        # 立即解码应该成功
        decoded_id = decode_token(token)
        assert decoded_id == user_id
        
        # 等待过期后解码应该失败
        import time
        time.sleep(2)
        
        decoded_id = decode_token(token)
        assert decoded_id is None