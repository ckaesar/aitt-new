"""
元数据同步摘要模型
"""
from sqlalchemy import Column, BigInteger, Integer, DateTime, Index
from sqlalchemy.sql import func

from app.core.database import Base


class MetadataSyncSummary(Base):
    __tablename__ = "aitt_metadata_sync_summaries"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="记录ID")

    sources_total = Column(Integer, nullable=False, default=0, comment="数据源总数")
    tables_total = Column(Integer, nullable=False, default=0, comment="数据表总数")
    columns_total = Column(Integer, nullable=False, default=0, comment="字段总数")

    deleted_sources = Column(Integer, nullable=False, default=0, comment="删除的数据源数")
    deleted_tables = Column(Integer, nullable=False, default=0, comment="删除的数据表数")
    deleted_columns = Column(Integer, nullable=False, default=0, comment="删除的字段数")

    upserted_sources = Column(Integer, nullable=False, default=0, comment="新增/更新的数据源数")
    upserted_tables = Column(Integer, nullable=False, default=0, comment="新增/更新的数据表数")
    upserted_columns = Column(Integer, nullable=False, default=0, comment="新增/更新的字段数")

    last_sync_time = Column(DateTime(timezone=True), nullable=True, comment="最近同步时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="记录创建时间")

    __table_args__ = (
        Index("idx_last_sync_time", "last_sync_time"),
        Index("idx_created_at", "created_at"),
    )

    def to_dict(self):
        return {
            "sources_total": self.sources_total or 0,
            "tables_total": self.tables_total or 0,
            "columns_total": self.columns_total or 0,
            "deleted_sources": self.deleted_sources or 0,
            "deleted_tables": self.deleted_tables or 0,
            "deleted_columns": self.deleted_columns or 0,
            "upserted_sources": self.upserted_sources or 0,
            "upserted_tables": self.upserted_tables or 0,
            "upserted_columns": self.upserted_columns or 0,
            "last_sync_time": (self.last_sync_time.isoformat() if self.last_sync_time else None),
        }