#avl tree for the events(the node), this is the main tree
class AVLNode:
    #the real node with value Event
    def __init__(self, event):
        self.event = event
        self.left = None
        self.right = None
        self.height = 0  # Leaf node height starts at 0

    @property
    def key(self) -> tuple:
        #returns the key aka the value of the node
        return self.event.key


class AVLTree:
    #avl tree with autobalancing and stress
    def __init__(self):
        self.root = None
        
        # Metrics tracking required by Section 14
        self.ll_rotations = 0
        self.rr_rotations = 0
        self.lr_rotations = 0
        self.rl_rotations = 0

    def get_height(self, node: AVLNode) -> int:
        #get the height of the node, -1 if its none
        return node.height if node else -1

    def get_balance_factor(self, node: AVLNode) -> int:
        #just calculates what node is more valuable than the other, using each node key
        if not node:
            return 0
        return self.get_height(node.left) - self.get_height(node.right)

    def update_height(self, node: AVLNode):
        #it calculates the height based on the node children
        if node:
            node.height = 1 + max(self.get_height(node.left), self.get_height(node.right))

    # --- Rotation Operations ---
    def _rotate_right(self, y: AVLNode) -> AVLNode:
        #single right rotation
        x = y.left
        T2 = x.right

        # Perform rotation
        x.right = y
        y.left = T2

        # Update heights
        self.update_height(y)
        self.update_height(x)

        return x

    def _rotate_left(self, x: AVLNode) -> AVLNode:
        #single left rotation
        y = x.right
        T2 = y.left

        # Perform rotation
        y.left = x
        x.right = T2

        # Update heights
        self.update_height(x)
        self.update_height(y)

        return y

        #Insertion
    def insert(self, event, auto_balance: bool = True):
        """Inserts a new event into the tree."""
        self.root = self._insert_node(self.root, event, auto_balance)

    def _insert_node(self, node: AVLNode, event, auto_balance: bool) -> AVLNode:
        # 1. Standard BST insertion
        if not node:
            return AVLNode(event)

        if event.key < node.key:
            node.left = self._insert_node(node.left, event, auto_balance)
        elif event.key > node.key:
            node.right = self._insert_node(node.right, event, auto_balance)
        else:
            return node  # Duplicate keys are not inserted

        # 2. Update height
        self.update_height(node)

        # If auto_balance is False (Stress Mode), skip rotations
        if not auto_balance:
            return node

        # 3. Check balance factor and apply rotations if needed
        balance = self.get_balance_factor(node)

        # Case LL
        if balance > 1 and event.key < node.left.key:
            self.ll_rotations += 1
            return self._rotate_right(node)

        # Case RR
        if balance < -1 and event.key > node.right.key:
            self.rr_rotations += 1
            return self._rotate_left(node)

        # Case LR
        if balance > 1 and event.key > node.left.key:
            self.lr_rotations += 1
            node.left = self._rotate_left(node.left)
            return self._rotate_right(node)

        # Case RL
        if balance < -1 and event.key < node.right.key:
            self.rl_rotations += 1
            node.right = self._rotate_right(node.right)
            return self._rotate_left(node)

        return node

    # --- Deletion ---
    def delete(self, key: tuple, auto_balance: bool = True):
        #deletes node with the given key from it
        self.root = self._delete_node(self.root, key, auto_balance)

    def _delete_node(self, node: AVLNode, key: tuple, auto_balance: bool) -> AVLNode:
        if not node:
            return node

        # 1. Locate node
        if key < node.key:
            node.left = self._delete_node(node.left, key, auto_balance)
        elif key > node.key:
            node.right = self._delete_node(node.right, key, auto_balance)
        else:
            # Node found
            if not node.left:
                return node.right
            elif not node.right:
                return node.left

            # Node with two children: get in-order successor (smallest in right subtree)
            successor = self._get_min_value_node(node.right)
            node.event = successor.event
            node.right = self._delete_node(node.right, successor.key, auto_balance)

        if not node:
            return node

        self.update_height(node)

        if not auto_balance:
            return node

        # Re-balance after deletion
        balance = self.get_balance_factor(node)

        if balance > 1 and self.get_balance_factor(node.left) >= 0:
            return self._rotate_right(node)
        if balance > 1 and self.get_balance_factor(node.left) < 0:
            node.left = self._rotate_left(node.left)
            return self._rotate_right(node)
        if balance < -1 and self.get_balance_factor(node.right) <= 0:
            return self._rotate_left(node)
        if balance < -1 and self.get_balance_factor(node.right) > 0:
            node.right = self._rotate_right(node.right)
            return self._rotate_left(node)

        return node

    def _get_min_value_node(self, node: AVLNode) -> AVLNode:
        current = node
        while current.left:
            current = current.left
        return current