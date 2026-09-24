# Entities

Entities have identity that persists through state changes.

## Table of Contents

- [Structure](#structure)
- [Factory Methods](#factory-methods)
- [Invariant Enforcement](#invariant-enforcement)
- [Aggregate Roots](#aggregate-roots)
- [Testing Entities](#testing-entities)

## Structure

```python
# Props dataclass for internal state
@dataclasses.dataclass
class TaskProps:
    id: str
    user_id: str
    title: str
    status: TaskStatus  # Value object
    created_at: datetime.datetime


class Task:
    # Private constructor enforces factory usage
    def __init__(self, props: TaskProps) -> None:
        self._props = props

    # Factory for new entities - validates business rules
    @classmethod
    def create(cls, *, user_id: str, title: str) -> 'Task':
        if not title or len(title.strip()) < 3:
            raise ValueError('Title must be at least 3 characters')
        return cls(
            TaskProps(
                id=str(uuid.uuid4()),
                user_id=user_id,
                title=title.strip(),
                status=TaskStatus.pending(),
                created_at=datetime.datetime.now(datetime.UTC),
            )
        )

    # Factory for reconstitution from persistence - no validation
    @classmethod
    def reconstitute(cls, props: TaskProps) -> 'Task':
        return cls(props)

    # Properties expose state (never setters)
    @property
    def id(self) -> str:
        return self._props.id

    @property
    def title(self) -> str:
        return self._props.title

    @property
    def is_completed(self) -> bool:
        return self._props.status.is_completed

    # Behavior methods enforce business rules
    def complete(self) -> None:
        if self._props.status.is_completed:
            raise ValueError('Task already completed')
        self._props.status = TaskStatus.completed()

    def rename(self, new_title: str) -> None:
        if not new_title or len(new_title.strip()) < 3:
            raise ValueError('Title must be at least 3 characters')
        self._props.title = new_title.strip()
```

## Factory Methods

Two factory methods serve different purposes:

| Method           | Purpose                      | Validates | Generates ID |
| ---------------- | ----------------------------- | --------- | ------------ |
| `create()`       | New entities from user input | Yes       | Yes          |
| `reconstitute()` | Rebuild from persistence     | No        | No           |

```python
# Application layer uses create()
task = Task.create(user_id='user-1', title='Buy milk')

# Repository uses reconstitute()
@classmethod
def reconstitute(cls, row: TaskRow) -> 'Task':
    return Task.reconstitute(
        TaskProps(
            id=row.id,
            user_id=row.user_id,
            title=row.title,
            status=TaskStatus.completed() if row.completed else TaskStatus.pending(),
            created_at=datetime.datetime.fromisoformat(row.created_at),
        )
    )
```

## Invariant Enforcement

Invariants are rules that must **always** be true:

```python
class Order:
    def __init__(self, props: OrderProps) -> None:
        # Constructor invariant: orders must have at least one item
        if len(props.items) == 0:
            raise ValueError('Order must have at least one item')
        self._props = props

    def add_item(self, item: LineItem) -> None:
        # Method invariant: no duplicates
        if any(i.product_id == item.product_id for i in self._props.items):
            raise ValueError('Product already in order')
        self._props.items.append(item)

    def remove_item(self, product_id: str) -> None:
        # Invariant: can't remove last item
        if len(self._props.items) == 1:
            raise ValueError('Cannot remove last item from order')
        self._props.items = [i for i in self._props.items if i.product_id != product_id]
```

## Aggregate Roots

Aggregate roots control access to child entities:

```python
class Order:
    def __init__(self, props: OrderProps) -> None:
        self._props = props

    # Child entities accessed through root
    @property
    def items(self) -> list[LineItem]:
        return list(self._props.items)  # Defensive copy

    # Modifications go through root's methods
    def add_item(self, product_id: str, quantity: int, price: Money) -> None:
        item = LineItem.create(product_id=product_id, quantity=quantity, price=price)
        self._props.items.append(item)
        self._recalculate_total()

    def _recalculate_total(self) -> None:
        total = Money.zero(self._props.currency)
        for item in self._props.items:
            total = total.add(item.subtotal)
        self._props.total = total
```

## Testing Entities

Domain entities are pure—test without mocks:

```python
class TestTaskCreate:
    def test_creates_task_with_valid_title(self) -> None:
        task = Task.create(user_id='user-1', title='Buy milk')

        assert task.title == 'Buy milk'
        assert task.is_completed is False
        assert task.id is not None

    def test_rejects_short_titles(self) -> None:
        with pytest.raises(ValueError, match='Title must be at least 3 characters'):
            Task.create(user_id='user-1', title='ab')

    def test_trims_whitespace(self) -> None:
        task = Task.create(user_id='user-1', title='  Buy milk  ')
        assert task.title == 'Buy milk'


class TestTaskComplete:
    def test_marks_pending_task_as_completed(self) -> None:
        task = Task.create(user_id='user-1', title='Test')
        task.complete()
        assert task.is_completed is True

    def test_throws_when_completing_twice(self) -> None:
        task = Task.create(user_id='user-1', title='Test')
        task.complete()
        with pytest.raises(ValueError, match='Task already completed'):
            task.complete()
```
