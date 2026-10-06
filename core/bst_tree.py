from core.event import Event


class BSTNode:
    #store the events used in avl

    def __init__(self, event: Event):
        self.value = event
        self.left_child = None
        self.right_child = None
        self.parent = None

    @property
    def key(self) -> tuple:
        return self.value.key

    def getValue(self) -> Event:
        return self.value

    def getLeftChild(self):
        return self.left_child

    def setLeftChild(self, node) -> None:
        self.left_child = node

    def getRightChild(self):
        return self.right_child

    def setRightChild(self, node) -> None:
        self.right_child = node

    def getFather(self):
        return self.parent

    def setFather(self, node) -> None:
        self.parent = node


class BinarySearchTree:
    #unbalanced bst tree made with the nodes in avl

    def __init__(self, events=()):
        self.root = None
        for event in events:
            self.insert(event)

    def insert(self, event: Event) -> bool:
        #insert by key
        node = BSTNode(event)
        if self.root is None:
            self.root = node
            return True

        current = self.root
        while True:
            if node.key == current.key:
                return False

            if node.key < current.key:
                child = current.getLeftChild()
                if child is None:
                    current.setLeftChild(node)
                    node.setFather(current)
                    return True
            else:
                child = current.getRightChild()
                if child is None:
                    current.setRightChild(node)
                    node.setFather(current)
                    return True
            current = child

    def search_by_key(self, key: tuple) -> BSTNode | None:
        #returns the node by key
        current = self.root
        while current is not None:
            if key == current.key:
                return current
            current = (
                current.getLeftChild()
                if key < current.key
                else current.getRightChild()
            )
        return None

    def search_comparisons(self, key: tuple) -> int:
        #returns the number of comparisons while searching the node
        comparisons = 0
        current = self.root
        while current is not None:
            comparisons += 1
            if key == current.key:
                break
            current = (
                current.getLeftChild()
                if key < current.key
                else current.getRightChild()
            )
        return comparisons

    def metrics(self) -> dict:
        #returns metrics and cost
        return measure_tree(self.root)


def measure_tree(root) -> dict:
    #measure the tree properties
    if root is None:
        return {
            "nodes": 0,
            "height": -1,
            "leaves": 0,
            "average_search_comparisons": 0,
        }

    node_count = 0
    leaf_count = 0
    max_depth = 0
    total_search_comparisons = 0
    stack = [(root, 0)]

    while stack:
        node, depth = stack.pop()
        node_count += 1
        max_depth = max(max_depth, depth)
        total_search_comparisons += depth + 1

        left = node.getLeftChild()
        right = node.getRightChild()
        if left is None and right is None:
            leaf_count += 1
        if right is not None:
            stack.append((right, depth + 1))
        if left is not None:
            stack.append((left, depth + 1))

    return {
        "nodes": node_count,
        "height": max_depth,
        "leaves": leaf_count,
        "average_search_comparisons": (
            total_search_comparisons / node_count
        ),
    }
