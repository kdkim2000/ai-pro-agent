# src/utils/logger.py
"""구조화 로거 — structlog 기반

전 Skill 실행 이력(입력·출력·판단 근거·게이트 결과)을 구조화하여
JSON 포맷으로 기록한다. 감사 추적(Audit Trail) 기반.
"""
import os
import logging
import structlog


def get_logger(name: str = "dev-lifecycle-agent") -> structlog.BoundLogger:
    """structlog 기반 구조화 로거 반환

    Args:
        name: 로거 이름

    Returns:
        구조화된 로거 인스턴스
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    # stdlib 로깅 기본 설정
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level, logging.INFO),
    )

    # structlog 설정
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level, logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger(name)
