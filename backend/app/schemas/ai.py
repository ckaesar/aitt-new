"""
AI相关schemas
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.ai_conversation import ConversationStatus, MessageRole


class AIQueryRequest(BaseModel):
    """AI查询请求模型"""
    query: str = Field(..., min_length=1, description="自然语言查询")
    conversation_id: Optional[int] = Field(None, description="对话ID，为空则创建新对话")
    data_source_id: Optional[int] = Field(None, description="指定数据源ID")
    context: Optional[Dict[str, Any]] = Field(None, description="额外上下文")
    use_rag: bool = Field(True, description="是否使用RAG")
    use_agent: bool = Field(True, description="是否使用Agent")


class AIQueryResponse(BaseModel):
    """AI查询响应模型（兼容前端字段命名）"""
    conversation_id: Optional[int] = Field(None, description="对话ID")
    message_id: Optional[int] = Field(None, description="消息ID")
    reply: str = Field(..., description="AI回复文本")
    generated_sql: Optional[str] = Field(None, description="生成的SQL")
    query_results: Optional[Dict[str, Any]] = Field(None, description="查询结果")
    suggestions: List[str] = Field([], description="建议")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="置信度")
    processing_time_ms: int = Field(..., description="处理时间毫秒")
    # RAG检索信息（用于前端引用来源展示与调试）
    rag_context: Optional[str] = Field(None, description="RAG拼接上下文（供提示词注入）")
    rag_chunks: List[Dict[str, Any]] = Field([], description="RAG检索片段列表[{source,text}]")
    # 新增结构化选择器信息
    tables: List[str] = Field([], description="涉及的表名列表")
    selected_table: Optional[str] = Field(None, description="推荐选择的主表")
    dimensions: List[str] = Field([], description="维度字段列表")
    metrics: List[Dict[str, Any]] = Field([], description="指标字段配置，包含聚合等")
    filters: List[Dict[str, Any]] = Field([], description="筛选条件列表")
    sorts: List[Dict[str, Any]] = Field([], description="排序字段列表")


class MessageResponse(BaseModel):
    """消息响应模型"""
    id: int = Field(..., description="消息ID")
    role: MessageRole = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    metadata: Optional[Dict[str, Any]] = Field(None, description="消息元数据")
    token_count: int = Field(..., description="Token数量")
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    """对话响应模型"""
    id: int = Field(..., description="对话ID")
    title: Optional[str] = Field(None, description="对话标题")
    status: ConversationStatus = Field(..., description="对话状态")
    total_messages: int = Field(..., description="消息总数")
    total_tokens: int = Field(..., description="Token总数")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    messages: List[MessageResponse] = Field([], description="消息列表")
    
    class Config:
        from_attributes = True


class ConversationCreateRequest(BaseModel):
    """创建对话请求模型"""
    title: Optional[str] = Field(None, max_length=200, description="对话标题")
    context: Optional[Dict[str, Any]] = Field(None, description="对话上下文")


class ConversationUpdateRequest(BaseModel):
    """更新对话请求模型"""
    title: Optional[str] = Field(None, max_length=200, description="对话标题")
    status: Optional[ConversationStatus] = Field(None, description="对话状态")


class AIAnalysisRequest(BaseModel):
    """AI分析请求模型"""
    data: List[Dict[str, Any]] = Field(..., description="待分析数据")
    analysis_type: str = Field(..., description="分析类型")
    parameters: Optional[Dict[str, Any]] = Field(None, description="分析参数")


class AIAnalysisResponse(BaseModel):
    """AI分析响应模型"""
    analysis_result: Dict[str, Any] = Field(..., description="分析结果")
    insights: List[str] = Field([], description="洞察")
    recommendations: List[str] = Field([], description="建议")
    charts: List[Dict[str, Any]] = Field([], description="图表配置")


class AIOptimizationRequest(BaseModel):
    """AI优化请求模型"""
    sql: str = Field(..., min_length=1, description="待优化的SQL")
    data_source_id: int = Field(..., description="数据源ID")
    optimization_goals: List[str] = Field([], description="优化目标")


class AIOptimizationResponse(BaseModel):
    """AI优化响应模型"""
    original_sql: str = Field(..., description="原始SQL")
    optimized_sql: str = Field(..., description="优化后的SQL")
    optimization_suggestions: List[str] = Field([], description="优化建议")
    performance_improvement: Optional[Dict[str, Any]] = Field(None, description="性能改进预估")


class PromptTemplateRequest(BaseModel):
    """Prompt模板请求模型"""
    template_name: str = Field(..., description="模板名称")
    variables: Dict[str, Any] = Field(..., description="模板变量")


class PromptTemplateResponse(BaseModel):
    """Prompt模板响应模型"""
    rendered_prompt: str = Field(..., description="渲染后的Prompt")
    template_name: str = Field(..., description="模板名称")
    variables_used: List[str] = Field([], description="使用的变量列表")