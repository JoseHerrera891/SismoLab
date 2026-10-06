#stress mode manager, function to the avl to recalculate all the balance when finish the mode.

class StressManager:
    def __init__(self, avl_tree):
        self.avl = avl_tree
        self.is_stress_mode = False

    def enable_stress_mode(self):
        #this deactivates the rotations when adding and deleting events to the tree
        self.is_stress_mode = True

    def disable_stress_mode(self):
        #does not make the tree to automatically balance, just daeactivates the stress mode
        self.is_stress_mode = False

    def recover_avl_balance(self) -> int:
        """Restore AVL balance in-place without rebuilding from sorted events."""
        rotations_before = sum(
            (
                self.avl.ll_rotations,
                self.avl.rr_rotations,
                self.avl.lr_rotations,
                self.avl.rl_rotations,
            )
        )
        expected_node_count = len(self._postorder_nodes())

        while True:
            rotated = False
            for node in self._postorder_nodes():
                self.avl._update_height(node)
                if abs(self.avl._get_balance_factor(node)) > 1:
                    self.avl._rebalance_node(node)
                    rotated = True
            if not rotated:
                break

        self._validate_recovered_tree(expected_node_count)
        self.is_stress_mode = False

        rotations_after = sum(
            (
                self.avl.ll_rotations,
                self.avl.rr_rotations,
                self.avl.lr_rotations,
                self.avl.rl_rotations,
            )
        )
        return rotations_after - rotations_before

    def _postorder_nodes(self):
        if self.avl.root is None:
            return []

        nodes = []
        stack = [(self.avl.root, False)]
        while stack:
            node, visited = stack.pop()
            if visited:
                nodes.append(node)
                continue
            stack.append((node, True))
            if node.getRightChild() is not None:
                stack.append((node.getRightChild(), False))
            if node.getLeftChild() is not None:
                stack.append((node.getLeftChild(), False))
        return nodes

    def _validate_recovered_tree(self, expected_node_count: int) -> None:
        if self.avl.root is not None and self.avl.root.getFather() is not None:
            raise RuntimeError("AVL recovery failed: root still has a parent.")

        visited = set()
        stack = [(self.avl.root, None, None, None)]
        while stack:
            node, parent, lower, upper = stack.pop()
            if node is None:
                continue
            if node in visited:
                raise RuntimeError("AVL recovery failed: cycle or shared node.")
            visited.add(node)
            if node.getFather() is not parent:
                raise RuntimeError("AVL recovery failed: invalid parent link.")
            if lower is not None and not lower < node.key:
                raise RuntimeError("AVL recovery failed: BST order is invalid.")
            if upper is not None and not node.key < upper:
                raise RuntimeError("AVL recovery failed: BST order is invalid.")

            stack.append((node.getRightChild(), node, node.key, upper))
            stack.append((node.getLeftChild(), node, lower, node.key))

        if len(visited) != expected_node_count:
            raise RuntimeError("AVL recovery failed: event count changed.")

        for node in self._postorder_nodes():
            left_height = self.avl._height(node.getLeftChild())
            right_height = self.avl._height(node.getRightChild())
            expected_height = 1 + max(left_height, right_height)
            if node.getHeight() != expected_height:
                raise RuntimeError("AVL recovery failed: invalid height metadata.")
            if abs(left_height - right_height) > 1:
                raise RuntimeError("AVL recovery failed: tree is still unbalanced.")