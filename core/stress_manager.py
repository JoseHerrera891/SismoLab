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
        #recovery process for the avl tree, performs the post-order balancing, until it reaches
        #the avl balance.
        rotations_before = (self.avl.ll_rotations + self.avl.rr_rotations + 
                            self.avl.lr_rotations + self.avl.rl_rotations)
        
        # Rebalance entire tree from bottom to top
        self.avl.root = self._rebalance_subtree(self.avl.root)
        if self.avl.root:
            self.avl.root.setFather(None)
        
        # Once recovered, return to normal mode
        self.is_stress_mode = False

        rotations_after = (self.avl.ll_rotations + self.avl.rr_rotations + 
                           self.avl.lr_rotations + self.avl.rl_rotations)
        
        return rotations_after - rotations_before

    def _rebalance_subtree(self, node):
        #recursively corrects the height and process the balance with post-order (for the node, subtree)
        if node is None:
            return None

        # 1. First, recursively recover left and right subtrees (Post-order)
        left = self._rebalance_subtree(node.getLeftChild())
        right = self._rebalance_subtree(node.getRightChild())

        node.setLeftChild(left)
        if left:
            left.setFather(node)

        node.setRightChild(right)
        if right:
            right.setFather(node)

        # 2. Recalculate current node height
        self.avl._update_height(node)

        # 3. Apply rotations using AVLtree internal balancer
        return self.avl._rebalance_node(node)