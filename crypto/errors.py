class CryptoError(Exception):
    """Base class error for crypto module"""

class ConfigError(CryptoError):
    """Invalid config profile parameters"""
