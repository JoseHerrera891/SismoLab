# core/event_manager.py


from core.event import Event

class EventManager:
    """Coordinates active events, historical/deleted IDs, and AVL synchronization."""
    def __init__(self, avl_tree):
        self.avl = avl_tree
        self.active_events = {}   # Map: event_id (int) -> Event object
        self.deleted_ids = set()   # Set of strictly deleted IDs (cannot be reused)
        self.archived_events = {} # Map: event_id (int) -> Event object (archived)

    def add_event(self, event: Event, auto_balance: bool = True) -> bool:
        """
        Registers a new event. 
        Rejects if the ID was previously deleted or is already active (Section 6).
        """
        if event.id in self.active_events or event.id in self.deleted_ids:
            return False
        
        self.active_events[event.id] = event
        self.avl.insert(event, auto_balance=auto_balance)
        return True

    def update_event(self, event_id: int, new_data: dict, auto_balance: bool = True) -> bool:
        """
        Updates an existing active event.
        If priority or magnitude changes, the key K changes, requiring node re-insertion.
        """
        if event_id not in self.active_events:
            return False

        event = self.active_events[event_id]
        old_key = event.key

        # Update event attributes dynamically
        for attr, value in new_data.items():
            if hasattr(event, attr) and attr != "id":
                setattr(event, attr, value)

        # Recalculate priority and update revision metadata
        event.priority = event.calculate_priority()
        event.revision += 1
        event.status = "PENDING"  # Any correction resets status to PENDING
        
        new_key = event.key

        # If key K changed, remove and re-insert in AVL to maintain valid BST order
        if old_key != new_key:
            self.avl.delete(old_key, auto_balance=auto_balance)
            self.avl.insert(event, auto_balance=auto_balance)

        return True

    def mark_as_reviewed(self, event_id: int) -> bool:
        """
        Marks an event as REVIEWED.
        Does NOT change key K, so no AVL re-insertion is required (Section 6).
        """
        if event_id not in self.active_events:
            return False
        
        self.active_events[event_id].status = "REVIEWED"
        return True

    def delete_event(self, event_id: int, auto_balance: bool = True) -> bool:
        """
        Deletes an individual event. 
        Removes it from active catalog and AVL, and records ID as deleted (Section 6).
        """
        if event_id not in self.active_events:
            return False

        event = self.active_events.pop(event_id)
        self.deleted_ids.add(event_id)
        self.avl.delete(event.key, auto_balance=auto_balance)
        return True

    def get_event(self, event_id: int) -> Event:
        """Fast O(1) lookup by event ID."""
        return self.active_events.get(event_id, None)