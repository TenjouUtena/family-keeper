import asyncio
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.pubsub import publish_list_event
from app.models import (
    FamilyList,
    FamilyMember,
    ItemAttachment,
    ItemStatus,
    ListItem,
    ListType,
    User,
)
from app.schemas.lists import (
    AttachmentResponse,
    BulkCreateItemsRequest,
    CreateItemRequest,
    CreateListRequest,
    ItemResponse,
    ListDetailResponse,
    ListResponse,
    ReorderItemsRequest,
    UpdateItemRequest,
    UpdateListRequest,
)
from app.services.push_service import notify_in_background

POSITION_GAP = 100


class ListService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # --- List CRUD ---

    async def create_list(
        self,
        family_id: UUID,
        data: CreateListRequest,
        member: FamilyMember,
        user: User,
    ) -> ListResponse:
        # Chore lists require parent role
        if data.list_type == "chores" and member.role.value != "parent":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only parents can create chore lists",
            )

        family_list = FamilyList(
            family_id=family_id,
            name=data.name,
            list_type=ListType(data.list_type),
            visible_to_role=data.visible_to_role,
            editable_by_role=data.editable_by_role,
            require_photo_completion=data.require_photo_completion,
            created_by=user.id,
        )
        self.db.add(family_list)
        await self.db.commit()
        await self.db.refresh(family_list)

        return ListResponse(
            id=family_list.id,
            family_id=family_list.family_id,
            name=family_list.name,
            list_type=family_list.list_type.value,
            visible_to_role=family_list.visible_to_role,
            editable_by_role=family_list.editable_by_role,
            require_photo_completion=family_list.require_photo_completion,
            is_archived=family_list.is_archived,
            created_by=family_list.created_by,
            created_at=family_list.created_at,
            updated_at=family_list.updated_at,
            item_count=0,
        )

    async def get_lists(
        self, family_id: UUID, member: FamilyMember
    ) -> list[ListResponse]:
        query = (
            select(
                FamilyList,
                func.count(ListItem.id).label("item_count"),
            )
            .outerjoin(ListItem, FamilyList.id == ListItem.list_id)
            .where(
                FamilyList.family_id == family_id,
                FamilyList.is_archived.is_(False),
            )
            .group_by(FamilyList.id)
            .order_by(FamilyList.created_at.desc())
        )

        # Filter by role visibility
        role = member.role.value
        query = query.where(
            (FamilyList.visible_to_role.is_(None))
            | (FamilyList.visible_to_role == role)
        )

        result = await self.db.execute(query)
        rows = result.all()

        return [
            ListResponse(
                id=fl.id,
                family_id=fl.family_id,
                name=fl.name,
                list_type=fl.list_type.value,
                visible_to_role=fl.visible_to_role,
                editable_by_role=fl.editable_by_role,
                require_photo_completion=fl.require_photo_completion,
                is_archived=fl.is_archived,
                created_by=fl.created_by,
                created_at=fl.created_at,
                updated_at=fl.updated_at,
                item_count=count,
            )
            for fl, count in rows
        ]

    async def get_list_detail(
        self, list_id: UUID, member: FamilyMember
    ) -> ListDetailResponse:
        result = await self.db.execute(
            select(FamilyList)
            .options(
                selectinload(FamilyList.items).selectinload(
                    ListItem.attachments
                )
            )
            .where(FamilyList.id == list_id)
        )
        family_list = result.scalar_one_or_none()

        if not family_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="List not found",
            )

        if family_list.family_id != member.family_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this family",
            )

        # Check role visibility
        role = member.role.value
        if (
            family_list.visible_to_role
            and family_list.visible_to_role != role
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not visible to your role",
            )

        # Batch-fetch usernames for completed_by
        completer_ids = {
            i.completed_by
            for i in family_list.items
            if i.completed_by
        }
        username_map: dict[UUID, str] = {}
        if completer_ids:
            result2 = await self.db.execute(
                select(User.id, User.username).where(
                    User.id.in_(completer_ids)
                )
            )
            username_map = dict(result2.all())

        items = [
            ItemResponse(
                id=item.id,
                list_id=item.list_id,
                content=item.content,
                notes=item.notes,
                status=item.status.value,
                position=item.position,
                assigned_to=item.assigned_to,
                due_date=item.due_date,
                completed_at=item.completed_at,
                completed_by=item.completed_by,
                completed_by_username=username_map.get(
                    item.completed_by
                ),
                created_at=item.created_at,
                attachments=[
                    AttachmentResponse.model_validate(a)
                    for a in item.attachments
                ],
            )
            for item in sorted(family_list.items, key=lambda i: i.position)
        ]

        return ListDetailResponse(
            id=family_list.id,
            family_id=family_list.family_id,
            name=family_list.name,
            list_type=family_list.list_type.value,
            visible_to_role=family_list.visible_to_role,
            editable_by_role=family_list.editable_by_role,
            require_photo_completion=family_list.require_photo_completion,
            is_archived=family_list.is_archived,
            created_by=family_list.created_by,
            created_at=family_list.created_at,
            updated_at=family_list.updated_at,
            item_count=len(items),
            items=items,
        )

    async def update_list(
        self, list_id: UUID, data: UpdateListRequest, member: FamilyMember
    ) -> ListResponse:
        family_list = await self._get_list_for_member(list_id, member)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(family_list, field, value)

        await self.db.commit()
        await self.db.refresh(family_list)
        await publish_list_event(list_id, "list_updated")

        count_result = await self.db.execute(
            select(func.count()).where(ListItem.list_id == list_id)
        )
        item_count = count_result.scalar_one()

        return ListResponse(
            id=family_list.id,
            family_id=family_list.family_id,
            name=family_list.name,
            list_type=family_list.list_type.value,
            visible_to_role=family_list.visible_to_role,
            editable_by_role=family_list.editable_by_role,
            require_photo_completion=family_list.require_photo_completion,
            is_archived=family_list.is_archived,
            created_by=family_list.created_by,
            created_at=family_list.created_at,
            updated_at=family_list.updated_at,
            item_count=item_count,
        )

    # --- Item CRUD ---

    async def add_item(
        self,
        list_id: UUID,
        data: CreateItemRequest,
        member: FamilyMember,
    ) -> ItemResponse:
        family_list = await self._get_list_for_member(list_id, member)
        self._check_editable(family_list, member)

        # Determine position
        if data.position is not None:
            position = data.position
        else:
            max_pos = await self.db.scalar(
                select(func.max(ListItem.position)).where(
                    ListItem.list_id == list_id
                )
            )
            position = (max_pos or 0) + POSITION_GAP

        item = ListItem(
            list_id=list_id,
            content=data.content,
            notes=data.notes,
            assigned_to=data.assigned_to,
            due_date=data.due_date,
            position=position,
        )
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        await publish_list_event(list_id, "item_created", {"item_id": str(item.id)})

        # Push: notify assignee
        if item.assigned_to and item.assigned_to != member.user_id:
            asyncio.create_task(
                notify_in_background(
                    self.db,
                    user_id=item.assigned_to,
                    title=f"{family_list.name}",
                    body=f'"{item.content}" assigned to you',
                    url=f"/families/{family_list.family_id}/lists/{list_id}",
                )
            )

        return ItemResponse(
            id=item.id,
            list_id=item.list_id,
            content=item.content,
            notes=item.notes,
            status=item.status.value,
            position=item.position,
            assigned_to=item.assigned_to,
            due_date=item.due_date,
            completed_at=item.completed_at,
            completed_by=item.completed_by,
            created_at=item.created_at,
        )

    async def bulk_add_items(
        self,
        list_id: UUID,
        data: BulkCreateItemsRequest,
        member: FamilyMember,
    ) -> list[ItemResponse]:
        family_list = await self._get_list_for_member(list_id, member)
        self._check_editable(family_list, member)

        max_pos = await self.db.scalar(
            select(func.max(ListItem.position)).where(
                ListItem.list_id == list_id
            )
        )
        start_pos = (max_pos or 0) + POSITION_GAP

        items = []
        for i, item_data in enumerate(data.items):
            item = ListItem(
                list_id=list_id,
                content=item_data.content,
                notes=item_data.notes,
                assigned_to=item_data.assigned_to,
                due_date=item_data.due_date,
                position=item_data.position
                if item_data.position is not None
                else start_pos + i * POSITION_GAP,
            )
            self.db.add(item)
            items.append(item)

        await self.db.commit()
        for item in items:
            await self.db.refresh(item)
        await publish_list_event(list_id, "items_created", {"count": len(items)})

        # Push: notify assignees of new items
        for item in items:
            if item.assigned_to and item.assigned_to != member.user_id:
                asyncio.create_task(
                    notify_in_background(
                        self.db,
                        user_id=item.assigned_to,
                        title=f"{family_list.name}",
                        body=f'"{item.content}" assigned to you',
                        url=f"/families/{family_list.family_id}/lists/{list_id}",
                    )
                )

        # Push: notify family about new grocery items
        if family_list.list_type == ListType.GROCERY:
            asyncio.create_task(
                notify_in_background(
                    self.db,
                    family_id=family_list.family_id,
                    title=f"{family_list.name}",
                    body=f"{len(items)} new item{'s' if len(items) > 1 else ''} added",
                    url=f"/families/{family_list.family_id}/lists/{list_id}",
                    exclude_user_id=member.user_id,
                )
            )

        return [
            ItemResponse(
                id=item.id,
                list_id=item.list_id,
                content=item.content,
                notes=item.notes,
                status=item.status.value,
                position=item.position,
                assigned_to=item.assigned_to,
                due_date=item.due_date,
                completed_at=item.completed_at,
                completed_by=item.completed_by,
                created_at=item.created_at,
            )
            for item in items
        ]

    async def update_item(
        self,
        list_id: UUID,
        item_id: UUID,
        data: UpdateItemRequest,
        member: FamilyMember,
        user: User,
    ) -> ItemResponse:
        family_list = await self._get_list_for_member(list_id, member)
        self._check_editable(family_list, member)

        item = await self.db.get(ListItem, item_id)
        if not item or item.list_id != list_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found",
            )

        update_data = data.model_dump(exclude_unset=True)

        # Handle status transition to done
        if "status" in update_data and update_data["status"] == "done":
            # Photo completion enforcement
            if family_list.require_photo_completion:
                photo_exists = await self.db.scalar(
                    select(func.count()).where(
                        ItemAttachment.item_id == item_id,
                        ItemAttachment.is_completion_photo.is_(True),
                        ItemAttachment.uploaded_by == user.id,
                    )
                )
                if not photo_exists:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Completion photo required",
                    )
            update_data["completed_at"] = datetime.now(UTC)
            update_data["completed_by"] = user.id
            update_data["status"] = ItemStatus.DONE
        elif "status" in update_data:
            new_status = ItemStatus(update_data["status"])
            # Only parents can undo a completed item
            if (
                item.status == ItemStatus.DONE
                and new_status != ItemStatus.DONE
                and member.role.value != "parent"
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only parents can undo completed items",
                )
            update_data["status"] = new_status
            if new_status != ItemStatus.DONE:
                update_data["completed_at"] = None
                update_data["completed_by"] = None

        # Track changes for push notifications
        old_assigned_to = item.assigned_to
        was_done = item.status == ItemStatus.DONE

        for field, value in update_data.items():
            setattr(item, field, value)

        await self.db.commit()
        await self.db.refresh(item)
        await publish_list_event(list_id, "item_updated", {"item_id": str(item.id)})

        # Push: notify on assignment change
        if (
            "assigned_to" in update_data
            and item.assigned_to
            and item.assigned_to != user.id
            and item.assigned_to != old_assigned_to
        ):
            asyncio.create_task(
                notify_in_background(
                    self.db,
                    user_id=item.assigned_to,
                    title=f"{family_list.name}",
                    body=f'"{item.content}" assigned to you',
                    url=f"/families/{family_list.family_id}/lists/{list_id}",
                )
            )

        # Push: notify family when item completed
        if not was_done and item.status == ItemStatus.DONE:
            asyncio.create_task(
                notify_in_background(
                    self.db,
                    family_id=family_list.family_id,
                    title=f"{family_list.name}",
                    body=f'"{item.content}" completed',
                    url=f"/families/{family_list.family_id}/lists/{list_id}",
                    exclude_user_id=user.id,
                )
            )

        # Load attachments
        att_result = await self.db.execute(
            select(ItemAttachment).where(
                ItemAttachment.item_id == item_id
            )
        )
        attachments = att_result.scalars().all()

        return ItemResponse(
            id=item.id,
            list_id=item.list_id,
            content=item.content,
            notes=item.notes,
            status=item.status.value,
            position=item.position,
            assigned_to=item.assigned_to,
            due_date=item.due_date,
            completed_at=item.completed_at,
            completed_by=item.completed_by,
            completed_by_username=await self._get_username(
                item.completed_by
            ),
            created_at=item.created_at,
            attachments=[
                AttachmentResponse.model_validate(a) for a in attachments
            ],
        )

    async def delete_item(
        self, list_id: UUID, item_id: UUID, member: FamilyMember
    ) -> None:
        family_list = await self._get_list_for_member(list_id, member)
        self._check_editable(family_list, member)

        item = await self.db.get(ListItem, item_id)
        if not item or item.list_id != list_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found",
            )

        await self.db.delete(item)
        await self.db.commit()
        await publish_list_event(list_id, "item_deleted", {"item_id": str(item_id)})

    async def reorder_items(
        self,
        list_id: UUID,
        data: ReorderItemsRequest,
        member: FamilyMember,
    ) -> list[ItemResponse]:
        await self._get_list_for_member(list_id, member)

        for reorder in data.items:
            item = await self.db.get(ListItem, reorder.id)
            if item and item.list_id == list_id:
                item.position = reorder.position

        await self.db.commit()
        await publish_list_event(list_id, "items_reordered")

        result = await self.db.execute(
            select(ListItem)
            .where(ListItem.list_id == list_id)
            .order_by(ListItem.position)
        )
        items = result.scalars().all()

        return [
            ItemResponse(
                id=item.id,
                list_id=item.list_id,
                content=item.content,
                notes=item.notes,
                status=item.status.value,
                position=item.position,
                assigned_to=item.assigned_to,
                due_date=item.due_date,
                completed_at=item.completed_at,
                completed_by=item.completed_by,
                created_at=item.created_at,
            )
            for item in items
        ]

    # --- Helpers ---

    async def _get_username(self, user_id: UUID | None) -> str | None:
        if not user_id:
            return None
        user = await self.db.get(User, user_id)
        return user.username if user else None

    async def _get_list_for_member(
        self, list_id: UUID, member: FamilyMember
    ) -> FamilyList:
        family_list = await self.db.get(FamilyList, list_id)
        if not family_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="List not found",
            )
        if family_list.family_id != member.family_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this family",
            )
        return family_list

    @staticmethod
    def _check_editable(
        family_list: FamilyList, member: FamilyMember
    ) -> None:
        if (
            family_list.editable_by_role
            and family_list.editable_by_role != member.role.value
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not editable by your role",
            )
