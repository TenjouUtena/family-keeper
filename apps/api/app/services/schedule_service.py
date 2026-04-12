import asyncio
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.pubsub import publish_schedule_event
from app.models import (
    FamilyMember,
    FamilySchedule,
    User,
)
from app.models.notification import NotificationType
from app.models.schedule_event import EventStatus, ScheduleEvent
from app.schemas.schedules import (
    BulkCreateEventsRequest,
    CreateEventRequest,
    CreateScheduleRequest,
    EventResponse,
    ScheduleDetailResponse,
    ScheduleResponse,
    UpdateEventRequest,
    UpdateScheduleRequest,
)
from app.services.notification_service import notify_in_background


class ScheduleService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # --- Schedule CRUD ---

    async def create_schedule(
        self,
        family_id: UUID,
        data: CreateScheduleRequest,
        member: FamilyMember,
        user: User,
    ) -> ScheduleResponse:
        schedule = FamilySchedule(
            family_id=family_id,
            name=data.name,
            description=data.description,
            visible_to_role=data.visible_to_role,
            editable_by_role=data.editable_by_role,
            created_by=user.id,
        )
        self.db.add(schedule)
        await self.db.commit()
        await self.db.refresh(schedule)

        return ScheduleResponse(
            id=schedule.id,
            family_id=schedule.family_id,
            name=schedule.name,
            description=schedule.description,
            visible_to_role=schedule.visible_to_role,
            editable_by_role=schedule.editable_by_role,
            is_archived=schedule.is_archived,
            created_by=schedule.created_by,
            created_at=schedule.created_at,
            updated_at=schedule.updated_at,
            event_count=0,
        )

    async def get_schedules(
        self, family_id: UUID, member: FamilyMember
    ) -> list[ScheduleResponse]:
        now = datetime.now(UTC)

        # Subquery for upcoming event date
        upcoming_subq = (
            select(func.min(ScheduleEvent.start_at))
            .where(
                ScheduleEvent.schedule_id == FamilySchedule.id,
                ScheduleEvent.status != EventStatus.DONE,
                ScheduleEvent.start_at >= now,
            )
            .correlate(FamilySchedule)
            .scalar_subquery()
        )

        query = (
            select(
                FamilySchedule,
                func.count(ScheduleEvent.id).label("event_count"),
                upcoming_subq.label("upcoming_event_at"),
            )
            .outerjoin(ScheduleEvent, FamilySchedule.id == ScheduleEvent.schedule_id)
            .where(
                FamilySchedule.family_id == family_id,
                FamilySchedule.is_archived.is_(False),
            )
            .group_by(FamilySchedule.id)
            .order_by(FamilySchedule.created_at.desc())
        )

        # Filter by role visibility
        role = member.role.value
        query = query.where(
            (FamilySchedule.visible_to_role.is_(None))
            | (FamilySchedule.visible_to_role == role)
        )

        result = await self.db.execute(query)
        rows = result.all()

        return [
            ScheduleResponse(
                id=sched.id,
                family_id=sched.family_id,
                name=sched.name,
                description=sched.description,
                visible_to_role=sched.visible_to_role,
                editable_by_role=sched.editable_by_role,
                is_archived=sched.is_archived,
                created_by=sched.created_by,
                created_at=sched.created_at,
                updated_at=sched.updated_at,
                event_count=count,
                upcoming_event_at=upcoming,
            )
            for sched, count, upcoming in rows
        ]

    async def get_schedule_detail(
        self, schedule_id: UUID, member: FamilyMember
    ) -> ScheduleDetailResponse:
        result = await self.db.execute(
            select(FamilySchedule)
            .options(selectinload(FamilySchedule.events))
            .where(FamilySchedule.id == schedule_id)
        )
        schedule = result.scalar_one_or_none()

        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schedule not found",
            )

        if schedule.family_id != member.family_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this family",
            )

        # Check role visibility
        role = member.role.value
        if schedule.visible_to_role and schedule.visible_to_role != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not visible to your role",
            )

        # Batch-fetch usernames for completed_by
        completer_ids = {
            e.completed_by for e in schedule.events if e.completed_by
        }
        username_map: dict[UUID, str] = {}
        if completer_ids:
            result2 = await self.db.execute(
                select(User.id, User.username).where(
                    User.id.in_(completer_ids)
                )
            )
            username_map = dict(result2.all())

        events = [
            EventResponse(
                id=event.id,
                schedule_id=event.schedule_id,
                title=event.title,
                description=event.description,
                start_at=event.start_at,
                end_at=event.end_at,
                all_day=event.all_day,
                status=event.status.value,
                assigned_to=event.assigned_to,
                completed_at=event.completed_at,
                completed_by=event.completed_by,
                completed_by_username=username_map.get(event.completed_by),
                location=event.location,
                notes=event.notes,
                created_at=event.created_at,
            )
            for event in sorted(schedule.events, key=lambda e: e.start_at)
        ]

        return ScheduleDetailResponse(
            id=schedule.id,
            family_id=schedule.family_id,
            name=schedule.name,
            description=schedule.description,
            visible_to_role=schedule.visible_to_role,
            editable_by_role=schedule.editable_by_role,
            is_archived=schedule.is_archived,
            created_by=schedule.created_by,
            created_at=schedule.created_at,
            updated_at=schedule.updated_at,
            event_count=len(events),
            events=events,
        )

    async def update_schedule(
        self, schedule_id: UUID, data: UpdateScheduleRequest, member: FamilyMember
    ) -> ScheduleResponse:
        schedule = await self._get_schedule_for_member(schedule_id, member)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(schedule, field, value)

        await self.db.commit()
        await self.db.refresh(schedule)
        await publish_schedule_event(schedule_id, "schedule_updated")

        count_result = await self.db.execute(
            select(func.count()).where(ScheduleEvent.schedule_id == schedule_id)
        )
        event_count = count_result.scalar_one()

        return ScheduleResponse(
            id=schedule.id,
            family_id=schedule.family_id,
            name=schedule.name,
            description=schedule.description,
            visible_to_role=schedule.visible_to_role,
            editable_by_role=schedule.editable_by_role,
            is_archived=schedule.is_archived,
            created_by=schedule.created_by,
            created_at=schedule.created_at,
            updated_at=schedule.updated_at,
            event_count=event_count,
        )

    # --- Event CRUD ---

    async def add_event(
        self,
        schedule_id: UUID,
        data: CreateEventRequest,
        member: FamilyMember,
    ) -> EventResponse:
        schedule = await self._get_schedule_for_member(schedule_id, member)
        self._check_editable(schedule, member)

        event = ScheduleEvent(
            schedule_id=schedule_id,
            title=data.title,
            description=data.description,
            start_at=data.start_at,
            end_at=data.end_at,
            all_day=data.all_day,
            assigned_to=data.assigned_to,
            location=data.location,
            notes=data.notes,
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        await publish_schedule_event(
            schedule_id, "event_created", {"event_id": str(event.id)}
        )

        # Notify assignee
        if event.assigned_to and event.assigned_to != member.user_id:
            asyncio.create_task(
                notify_in_background(
                    user_id=event.assigned_to,
                    family_id=schedule.family_id,
                    type=NotificationType.TASK_ASSIGNED,
                    title=f"{schedule.name}",
                    body=f'"{event.title}" assigned to you',
                    url=f"/families/{schedule.family_id}/schedules/{schedule_id}",
                )
            )

        return EventResponse(
            id=event.id,
            schedule_id=event.schedule_id,
            title=event.title,
            description=event.description,
            start_at=event.start_at,
            end_at=event.end_at,
            all_day=event.all_day,
            status=event.status.value,
            assigned_to=event.assigned_to,
            completed_at=event.completed_at,
            completed_by=event.completed_by,
            location=event.location,
            notes=event.notes,
            created_at=event.created_at,
        )

    async def bulk_add_events(
        self,
        schedule_id: UUID,
        data: BulkCreateEventsRequest,
        member: FamilyMember,
    ) -> list[EventResponse]:
        schedule = await self._get_schedule_for_member(schedule_id, member)
        self._check_editable(schedule, member)

        events = []
        for event_data in data.events:
            event = ScheduleEvent(
                schedule_id=schedule_id,
                title=event_data.title,
                description=event_data.description,
                start_at=event_data.start_at,
                end_at=event_data.end_at,
                all_day=event_data.all_day,
                assigned_to=event_data.assigned_to,
                location=event_data.location,
                notes=event_data.notes,
            )
            self.db.add(event)
            events.append(event)

        await self.db.commit()
        for event in events:
            await self.db.refresh(event)
        await publish_schedule_event(
            schedule_id, "events_created", {"count": len(events)}
        )

        # Notify assignees
        for event in events:
            if event.assigned_to and event.assigned_to != member.user_id:
                asyncio.create_task(
                    notify_in_background(
                        user_id=event.assigned_to,
                        family_id=schedule.family_id,
                        type=NotificationType.TASK_ASSIGNED,
                        title=f"{schedule.name}",
                        body=f'"{event.title}" assigned to you',
                        url=f"/families/{schedule.family_id}/schedules/{schedule_id}",
                    )
                )

        return [
            EventResponse(
                id=event.id,
                schedule_id=event.schedule_id,
                title=event.title,
                description=event.description,
                start_at=event.start_at,
                end_at=event.end_at,
                all_day=event.all_day,
                status=event.status.value,
                assigned_to=event.assigned_to,
                completed_at=event.completed_at,
                completed_by=event.completed_by,
                location=event.location,
                notes=event.notes,
                created_at=event.created_at,
            )
            for event in events
        ]

    async def update_event(
        self,
        schedule_id: UUID,
        event_id: UUID,
        data: UpdateEventRequest,
        member: FamilyMember,
        user: User,
    ) -> EventResponse:
        schedule = await self._get_schedule_for_member(schedule_id, member)
        self._check_editable(schedule, member)

        event = await self.db.get(ScheduleEvent, event_id)
        if not event or event.schedule_id != schedule_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found",
            )

        update_data = data.model_dump(exclude_unset=True)

        # Handle status transition to done
        if "status" in update_data and update_data["status"] == "done":
            update_data["completed_at"] = datetime.now(UTC)
            update_data["completed_by"] = user.id
            update_data["status"] = EventStatus.DONE
        elif "status" in update_data:
            new_status = EventStatus(update_data["status"])
            if (
                event.status == EventStatus.DONE
                and new_status != EventStatus.DONE
                and member.role.value != "parent"
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only parents can undo completed events",
                )
            update_data["status"] = new_status
            if new_status != EventStatus.DONE:
                update_data["completed_at"] = None
                update_data["completed_by"] = None

        # Track changes for notifications
        old_assigned_to = event.assigned_to
        was_done = event.status == EventStatus.DONE

        for field, value in update_data.items():
            setattr(event, field, value)

        await self.db.commit()
        await self.db.refresh(event)
        await publish_schedule_event(
            schedule_id, "event_updated", {"event_id": str(event.id)}
        )

        # Notify on assignment change
        if (
            "assigned_to" in update_data
            and event.assigned_to
            and event.assigned_to != user.id
            and event.assigned_to != old_assigned_to
        ):
            asyncio.create_task(
                notify_in_background(
                    user_id=event.assigned_to,
                    family_id=schedule.family_id,
                    type=NotificationType.TASK_ASSIGNED,
                    title=f"{schedule.name}",
                    body=f'"{event.title}" assigned to you',
                    url=f"/families/{schedule.family_id}/schedules/{schedule_id}",
                )
            )

        # Notify family when event completed
        if not was_done and event.status == EventStatus.DONE:
            asyncio.create_task(
                notify_in_background(
                    family_id=schedule.family_id,
                    type=NotificationType.TASK_COMPLETED,
                    title=f"{schedule.name}",
                    body=f'"{event.title}" completed',
                    url=f"/families/{schedule.family_id}/schedules/{schedule_id}",
                    exclude_user_id=user.id,
                )
            )

        return EventResponse(
            id=event.id,
            schedule_id=event.schedule_id,
            title=event.title,
            description=event.description,
            start_at=event.start_at,
            end_at=event.end_at,
            all_day=event.all_day,
            status=event.status.value,
            assigned_to=event.assigned_to,
            completed_at=event.completed_at,
            completed_by=event.completed_by,
            completed_by_username=await self._get_username(event.completed_by),
            location=event.location,
            notes=event.notes,
            created_at=event.created_at,
        )

    async def delete_event(
        self, schedule_id: UUID, event_id: UUID, member: FamilyMember
    ) -> None:
        schedule = await self._get_schedule_for_member(schedule_id, member)
        self._check_editable(schedule, member)

        event = await self.db.get(ScheduleEvent, event_id)
        if not event or event.schedule_id != schedule_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found",
            )

        await self.db.delete(event)
        await self.db.commit()
        await publish_schedule_event(
            schedule_id, "event_deleted", {"event_id": str(event_id)}
        )

    # --- Helpers ---

    async def _get_username(self, user_id: UUID | None) -> str | None:
        if not user_id:
            return None
        user = await self.db.get(User, user_id)
        return user.username if user else None

    async def _get_schedule_for_member(
        self, schedule_id: UUID, member: FamilyMember
    ) -> FamilySchedule:
        schedule = await self.db.get(FamilySchedule, schedule_id)
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schedule not found",
            )
        if schedule.family_id != member.family_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this family",
            )
        return schedule

    @staticmethod
    def _check_editable(
        schedule: FamilySchedule, member: FamilyMember
    ) -> None:
        if (
            schedule.editable_by_role
            and schedule.editable_by_role != member.role.value
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not editable by your role",
            )
