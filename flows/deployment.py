"""
Скрипт для создания деплоя Prefect с расписанием
"""
from prefect.deployments import Deployment
from prefect.client.schemas.schedules import CronSchedule

from flows.prefect_flow import monitoring_flow


def create_deployment():
    """Создание деплоя с ежедневным расписанием в 9:00 МСК"""
    deployment = Deployment.build_from_flow(
        flow=monitoring_flow,
        name="bn-spb-daily",
        work_pool_name="default",
        schedules=[
            CronSchedule(
                cron="0 9 * * *",  # Каждый день в 9:00
                timezone="Europe/Moscow"
            )
        ],
        tags=["production", "bn", "spb"],
        description="Ежедневный мониторинг рынка аренды Санкт-Петербурга (BN.ru)"
    )

    deployment.apply()
    print("Деплой создан успешно!")
    print("Запустите сервер Prefect: prefect server start")
    print("Запустите воркер: prefect worker start --pool default")


if __name__ == "__main__":
    create_deployment()


    