#event manager for lifecycle  without modifing the avl tree

from core.event import Event

class EventManager:
    def __init__(self, avl_tree):
        self.avl = avl_tree
        self.active_events = {}   # Map: event_id (int) -> Event object
        self.deleted_ids = set()   # Set of strictly deleted IDs (cannot be reused)
        self.archived_events = {} # Map: event_id (int) -> Event object (archived)

    def add_event(self, event: Event, auto_balance: bool = True) -> bool:
        #registers a new event, if it was deleted previously (by id) or if it is active, cannot be added.
        if (
            event.id in self.active_events
            or event.id in self.deleted_ids
            or event.id in self.archived_events
        ):
            return False
        
        self.active_events[event.id] = event
        self.avl.insert(event, auto_balance=auto_balance)
        return True

    def update_event(self, event_id: int, new_data: dict, auto_balance: bool = True) -> bool:
        if event_id not in self.active_events:
            return False

        event = self.active_events[event_id]
        old_key = event.key
        editable_fields = {"magnitude", "depth", "x", "y", "is_populated"}
        if not isinstance(new_data, dict):
            raise TypeError("Event updates must be provided as a dictionary.")
        unsupported_fields = set(new_data) - editable_fields
        if unsupported_fields:
            fields = ", ".join(
                str(field) for field in sorted(unsupported_fields, key=str)
            )
            raise ValueError(f"Unsupported event update field(s): {fields}.")

        corrected_event = Event(
            event_id=event.id,
            magnitude=new_data.get("magnitude", event.magnitude),
            depth=new_data.get("depth", event.depth),
            x=new_data.get("x", event.x),
            y=new_data.get("y", event.y),
            timestamp=event.timestamp,
            station=event.station,
            is_populated=new_data.get("is_populated", event.is_populated),
        )
        corrected_event.accepted_stations = event.accepted_stations.copy()
        corrected_event.revision = event.revision + 1
        corrected_event.status = "PENDING"
        new_key = corrected_event.key

        if old_key != new_key:
            self.avl.delete(old_key, auto_balance=auto_balance)
        event.__dict__.update(corrected_event.__dict__)
        if old_key != new_key:
            self.avl.insert(event, auto_balance=auto_balance)

        return True

    def mark_as_reviewed(self, event_id: int) -> bool:
        #maks event as reviewed
        if event_id not in self.active_events:
            return False
        
        self.active_events[event_id].status = "REVIEWED"
        return True

    def delete_event(self, event_id: int, auto_balance: bool = True) -> bool:
        #deletes an event, pop it from the active event, add the id to the deleted, then delete from the tree
        if event_id not in self.active_events:
            return False

        event = self.active_events.pop(event_id)
        self.deleted_ids.add(event_id)
        self.avl.delete(event.key, auto_balance=auto_balance)
        return True

    def get_event(self, event_id: int) -> Event:
        #get the event id
        return self.active_events.get(event_id, None)