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
        
        # Once recovered, return to normal mode
        self.is_stress_mode = False

        rotations_after = (self.avl.ll_rotations + self.avl.rr_rotations + 
                           self.avl.lr_rotations + self.avl.rl_rotations)
        
        return rotations_after - rotations_before

    def _rebalance_subtree(self, node):
        #recursively corrects the height and process the balance with post-order (for the node, subtree)
        if not node:
            return None

        # 1. First, recursively recover left and right subtrees (Post-order)
        node.left = self._rebalance_subtree(node.left)
        node.right = self._rebalance_subtree(node.right)

        # 2. Recalculate current node height
        self.avl.update_height(node)
        
        # 3. Check balance factor
        balance = self.avl.get_balance_factor(node)

        # Left heavy (|BF| > 1)
        if balance > 1:
            if self.avl.get_balance_factor(node.left) < 0:
                # Left-Right (LR) Case
                self.avl.lr_rotations += 1
                node.left = self.avl._rotate_left(node.left)
            else:
                # Left-Left (LL) Case
                self.avl.ll_rotations += 1
            return self.avl._rotate_right(node)

        # Right heavy (|BF| < -1)
        if balance < -1:
            if self.avl.get_balance_factor(node.right) > 0:
                # Right-Left (RL) Case
                self.avl.rl_rotations += 1
                node.right = self.avl._rotate_right(node.right)
            else:
                # Right-Right (RR) Case
                self.avl.rr_rotations += 1
            return self.avl._rotate_left(node)

        return node