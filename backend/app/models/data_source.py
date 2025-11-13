"""
数据源相关模型
"""
from sqlalchemy import (
    Column, BigInteger, String, Boolean, DateTime, Enum, 
    Text, Integer, ForeignKey, JSON, DECIMAL, Index, UniqueConstraint
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class DataSourceType(str, enum.Enum):
    """数据源类型枚举"""
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    CLICKHOUSE = "clickhouse"
    HIVE = "hive"


class DataSource(Base):
    """数据源表"""
    __tablename__ = "aitt_data_sources"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="数据源ID")
    name = Column(String(100), nullable=False, comment="数据源名称")
    type = Column(Enum(DataSourceType), nullable=False, comment="数据源类型")
    host = Column(String(255), nullable=False, comment="主机地址")
    port = Column(Integer, nullable=False, comment="端口")
    database_name = Column(String(100), nullable=False, comment="数据库名")
    username = Column(String(100), comment="用户名")
    password_encrypted = Column(Text, comment="加密密码")
    description = Column(Text, comment="描述")
    is_active = Column(Boolean, default=True, comment="是否激活")
    created_by = Column(BigInteger, ForeignKey("aitt_users.id"), nullable=False, comment="创建人")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        comment="更新时间"
    )
    
    # 关系
    creator = relationship("User", back_populates="created_data_sources")
    tables = relationship("DataTable", back_populates="data_source", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index("idx_name", "name"),
        Index("idx_type", "type"),
        Index("idx_is_active", "is_active"),
    )
    
    def __repr__(self):
        return f"<DataSource(id={self.id}, name='{self.name}', type='{self.type}')>"


class DataTable(Base):
    """数据表元信息"""
    __tablename__ = "aitt_data_tables"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="表ID")
    data_source_id = Column(BigInteger, ForeignKey("aitt_data_sources.id"), nullable=False, comment="数据源ID")
    table_name = Column(String(100), nullable=False, comment="表名")
    display_name = Column(String(100), comment="显示名称")
    description = Column(Text, comment="表描述")
    category = Column(String(50), comment="分类")
    tags = Column(JSON, comment="标签")
    row_count = Column(BigInteger, default=0, comment="行数")
    size_mb = Column(DECIMAL(10, 2), default=0, comment="大小MB")
    last_updated = Column(DateTime(timezone=True), comment="最后更新时间")
    is_active = Column(Boolean, default=True, comment="是否激活")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        comment="更新时间"
    )
    
    # 关系
    data_source = relationship("DataSource", back_populates="tables")
    columns = relationship("TableColumn", back_populates="table", cascade="all, delete-orphan")
    
    # 索引和约束
    __table_args__ = (
        UniqueConstraint("data_source_id", "table_name", name="uk_source_table"),
        Index("idx_table_name", "table_name"),
        Index("idx_category", "category"),
        Index("idx_is_active", "is_active"),
    )
    
    def __repr__(self):
        return f"<DataTable(id={self.id}, table_name='{self.table_name}')>"


class TableColumn(Base):
    """字段元信息"""
    __tablename__ = "aitt_table_columns"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="字段ID")
    table_id = Column(BigInteger, ForeignKey("aitt_data_tables.id"), nullable=False, comment="表ID")
    column_name = Column(String(100), nullable=False, comment="字段名")
    display_name = Column(String(100), comment="显示名称")
    data_type = Column(String(50), nullable=False, comment="数据类型")
    is_nullable = Column(Boolean, default=True, comment="是否可空")
    default_value = Column(String(255), comment="默认值")
    description = Column(Text, comment="字段描述")
    is_dimension = Column(Boolean, default=False, comment="是否维度")
    is_metric = Column(Boolean, default=False, comment="是否指标")
    is_primary_key = Column(Boolean, default=False, comment="是否主键")
    is_foreign_key = Column(Boolean, default=False, comment="是否外键")
    column_order = Column(Integer, default=0, comment="字段顺序")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        comment="更新时间"
    )
    
    # 关系
    table = relationship("DataTable", back_populates="columns")
    
    # 索引和约束
    __table_args__ = (
        UniqueConstraint("table_id", "column_name", name="uk_table_column"),
        Index("idx_column_name", "column_name"),
        Index("idx_is_dimension", "is_dimension"),
        Index("idx_is_metric", "is_metric"),
        Index("idx_column_order", "column_order"),
    )
    
    def __repr__(self):
        return f"<TableColumn(id={self.id}, column_name='{self.column_name}', data_type='{self.data_type}')>"