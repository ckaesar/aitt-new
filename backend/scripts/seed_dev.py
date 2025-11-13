import asyncio
import os
import sys
from sqlalchemy import select

# 将backend目录加入sys.path，确保可导入app包
CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# 确保模型被注册到Base.metadata
from app.models import user as user_model
from app.models import data_source as ds_model

from app.core.database import AsyncSessionLocal, init_db
from app.utils.security import get_password_hash


async def seed():
    # 创建表（需要模型已导入）
    await init_db()

    async with AsyncSessionLocal() as session:
        # 检查是否已存在管理员
        existing_admin = await session.execute(
            select(user_model.User).where(user_model.User.username == "admin")
        )
        existing_admin = existing_admin.scalar_one_or_none()

        if existing_admin is None:
            admin = user_model.User(
                username="admin",
                email="admin@example.com",
                password_hash=get_password_hash("admin123"),
                full_name="系统管理员",
                department="IT",
                role=user_model.UserRole.ADMIN,
                is_active=True,
            )
            session.add(admin)
            await session.flush()  # 获取admin.id
        else:
            admin = existing_admin

        # 插入一个示例数据源
        existing_ds = await session.execute(
            select(ds_model.DataSource).where(ds_model.DataSource.name == "本地示例源")
        )
        existing_ds = existing_ds.scalar_one_or_none()

        if existing_ds is None:
            ds = ds_model.DataSource(
                name="本地示例源",
                type=ds_model.DataSourceType.MYSQL,
                host="localhost",
                port=3306,
                database_name="demo_db",
                username="root",
                description="用于演示的数据源元信息",
                is_active=True,
                created_by=admin.id,
            )
            session.add(ds)
            await session.flush()
        else:
            ds = existing_ds

        # 插入示例数据表及字段
        # 表：customers
        existing_customers = await session.execute(
            select(ds_model.DataTable).where(
                (ds_model.DataTable.data_source_id == ds.id)
                & (ds_model.DataTable.table_name == "customers")
            )
        )
        existing_customers = existing_customers.scalar_one_or_none()

        if existing_customers is None:
            customers = ds_model.DataTable(
                data_source_id=ds.id,
                table_name="customers",
                display_name="客户信息",
                description="客户基础信息表",
                category="crm",
                tags=["demo", "crm"],
                is_active=True,
            )
            session.add(customers)
            await session.flush()

            session.add_all([
                ds_model.TableColumn(
                    table_id=customers.id, column_name="customer_id",
                    display_name="客户ID", data_type="bigint", is_primary_key=True, is_dimension=True, column_order=1
                ),
                ds_model.TableColumn(
                    table_id=customers.id, column_name="name",
                    display_name="姓名", data_type="varchar(100)", is_dimension=True, column_order=2
                ),
                ds_model.TableColumn(
                    table_id=customers.id, column_name="email",
                    display_name="邮箱", data_type="varchar(100)", is_dimension=True, column_order=3
                ),
                ds_model.TableColumn(
                    table_id=customers.id, column_name="created_at",
                    display_name="创建时间", data_type="datetime", is_dimension=True, column_order=4
                ),
            ])

        # 表：sales_orders
        existing_orders = await session.execute(
            select(ds_model.DataTable).where(
                (ds_model.DataTable.data_source_id == ds.id)
                & (ds_model.DataTable.table_name == "sales_orders")
            )
        )
        existing_orders = existing_orders.scalar_one_or_none()

        if existing_orders is None:
            orders = ds_model.DataTable(
                data_source_id=ds.id,
                table_name="sales_orders",
                display_name="销售订单",
                description="订单明细和金额",
                category="sales",
                tags=["demo", "sales"],
                is_active=True,
            )
            session.add(orders)
            await session.flush()

            session.add_all([
                ds_model.TableColumn(
                    table_id=orders.id, column_name="order_id",
                    display_name="订单ID", data_type="bigint", is_primary_key=True, is_dimension=True, column_order=1
                ),
                ds_model.TableColumn(
                    table_id=orders.id, column_name="customer_id",
                    display_name="客户ID", data_type="bigint", is_foreign_key=True, is_dimension=True, column_order=2
                ),
                ds_model.TableColumn(
                    table_id=orders.id, column_name="order_date",
                    display_name="下单日期", data_type="date", is_dimension=True, column_order=3
                ),
                ds_model.TableColumn(
                    table_id=orders.id, column_name="amount",
                    display_name="订单金额", data_type="decimal(10,2)", is_metric=True, column_order=4
                ),
                ds_model.TableColumn(
                    table_id=orders.id, column_name="status",
                    display_name="订单状态", data_type="varchar(50)", is_dimension=True, column_order=5
                ),
            ])

        await session.commit()
        print("开发环境种子数据插入完成：管理员、数据源与示例表/字段。")


if __name__ == "__main__":
    asyncio.run(seed())