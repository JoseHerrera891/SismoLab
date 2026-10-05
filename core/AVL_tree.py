class AVLnode:
    def __init__(self, event):
        self.value = event
        self.height = 0
        self.leftChild = None
        self.rightChild = None
        self.father = None

    def getValue(self):
        return self.value

    def setValue(self, value):
        self.value = value

    def getLeftChild(self):
        return self.leftChild

    def setLeftChild(self, node):
        self.leftChild = node

    def getRightChild(self):
        return self.rightChild

    def setRightChild(self, node):
        self.rightChild = node

    def getFather(self):
        return self.father

    def setFather(self, node):
        self.father = node

    def getHeight(self):
        return self.height

    def setHeight(self, height):
        self.height = height

    @property
    def key(self) -> tuple:
        return self.value.key


class AVLtree:
    def __init__(self):
        self.raiz = None
        
        # Metrics tracking
        self.ll_rotations = 0
        self.rr_rotations = 0
        self.lr_rotations = 0
        self.rl_rotations = 0

    # Auto balance
    def _height(self, node):
        if node is None:
            return -1
        return node.getHeight()

    def _update_height(self, node):
        if node is not None:
            leftHeight = self._height(node.getLeftChild())
            rightHeight = self._height(node.getRightChild())
            node.setHeight(1 + max(leftHeight, rightHeight))

    def _get_balance_factor(self, node):
        if node is None:
            return 0
        return self._height(node.getLeftChild()) - self._height(node.getRightChild())

    # Rotations
    def _rotate_right(self, sup):
        """Single right rotation (LL)."""
        middle = sup.getLeftChild()
        aux = middle.getRightChild()

        if aux is not None:
            aux.setFather(sup)

        middle.setRightChild(sup)
        sup.setLeftChild(aux)

        sup_father = sup.getFather()
        middle.setFather(sup_father)
        sup.setFather(middle)

        if sup_father is None:
            self.raiz = middle
        elif sup_father.getLeftChild() == sup:
            sup_father.setLeftChild(middle)
        else:
            sup_father.setRightChild(middle)

        self._update_height(sup)
        self._update_height(middle)
        return middle

    def _rotate_left(self, sup):
        """Single left rotation (RR)."""
        middle = sup.getRightChild()
        aux = middle.getLeftChild()

        if aux is not None:
            aux.setFather(sup)

        middle.setLeftChild(sup)
        sup.setRightChild(aux)

        sup_father = sup.getFather()
        middle.setFather(sup_father)
        sup.setFather(middle)

        if sup_father is None:
            self.raiz = middle
        elif sup_father.getLeftChild() == sup:
            sup_father.setLeftChild(middle)
        else:
            sup_father.setRightChild(middle)

        self._update_height(sup)
        self._update_height(middle)
        return middle

    # insert
    def insert(self, event, auto_balance: bool = True):
        node = AVLnode(event)
        if self.raiz is None:
            self.raiz = node
            node.setFather(None)
        else:
            self._insert(node, self.raiz, auto_balance)

    def _insert(self, node, currentRoot, auto_balance: bool):
        if currentRoot.key == node.key:
            return  # Clave duplicada

        if node.key < currentRoot.key:
            left = currentRoot.getLeftChild()
            if left is None:
                currentRoot.setLeftChild(node)
                node.setFather(currentRoot)
            else:
                self._insert(node, left, auto_balance)
        else:
            right = currentRoot.getRightChild()
            if right is None:
                currentRoot.setRightChild(node)
                node.setFather(currentRoot)
            else:
                self._insert(node, right, auto_balance)

        self._update_height(currentRoot)

        if auto_balance:
            self._rebalance_node(currentRoot)

    # search and eliminate
    def search_by_key(self, key_tuple):
        if self.raiz is None:
            return None
        return self._search(key_tuple, self.raiz)

    def _search(self, key_tuple, currentRoot):
        if currentRoot is None:
            return None
        if key_tuple == currentRoot.key:
            return currentRoot
        if key_tuple < currentRoot.key:
            return self._search(key_tuple, currentRoot.getLeftChild())
        return self._search(key_tuple, currentRoot.getRightChild())

    def delete(self, key_tuple, auto_balance: bool = True):
        node = self.search_by_key(key_tuple)
        if node is not None:
            self._delete(node, auto_balance)

    def _delete(self, node, auto_balance: bool):
        father = node.getFather()

        # Case 1. leaf
        if node.getLeftChild() is None and node.getRightChild() is None:
            if father is None:
                self.raiz = None
            elif father.getLeftChild() == node:
                father.setLeftChild(None)
            else:
                father.setRightChild(None)
            node.setFather(None)
            if auto_balance and father:
                self._rebalance_ancestors(father)
            return

        # Case 2. only right child
        if node.getLeftChild() is None:
            child = node.getRightChild()
            if father is None:
                self.raiz = child
                child.setFather(None)
            else:
                if father.getLeftChild() == node:
                    father.setLeftChild(child)
                else:
                    father.setRightChild(child)
                child.setFather(father)
            if auto_balance and father:
                self._rebalance_ancestors(father)
            return

        # Case 3. only left child
        if node.getRightChild() is None:
            child = node.getLeftChild()
            if father is None:
                self.raiz = child
                child.setFather(None)
            else:
                if father.getLeftChild() == node:
                    father.setLeftChild(child)
                else:
                    father.setRightChild(child)
                child.setFather(father)
            if auto_balance and father:
                self._rebalance_ancestors(father)
            return

        # Case 4. two childs
        predecessor = self._get_predecessor(node)
        node.setValue(predecessor.getValue())
        self._delete(predecessor, auto_balance)

    def _get_predecessor(self, node):
        actual = node.getLeftChild()
        while actual.getRightChild() is not None:
            actual = actual.getRightChild()
        return actual

    # Balance cases
    def _rebalance_node(self, node):
        fb = self._get_balance_factor(node)
        
        # Case LL
        if fb > 1 and self._get_balance_factor(node.getLeftChild()) >= 0:
            self.ll_rotations += 1
            return self._rotate_right(node)

        # Case LR
        if fb > 1 and self._get_balance_factor(node.getLeftChild()) < 0:
            self.lr_rotations += 1
            node.setLeftChild(self._rotate_left(node.getLeftChild()))
            return self._rotate_right(node)

        # Case RR
        if fb < -1 and self._get_balance_factor(node.getRightChild()) <= 0:
            self.rr_rotations += 1
            return self._rotate_left(node)

        # Case RL
        if fb < -1 and self._get_balance_factor(node.getRightChild()) > 0:
            self.rl_rotations += 1
            node.setRightChild(self._rotate_right(node.getRightChild()))
            return self._rotate_left(node)

        return node

    def _rebalance_ancestors(self, nodo):
        currentNode = nodo
        while currentNode is not None:
            self._update_height(currentNode)
            next_father = currentNode.getFather()
            self._rebalance_node(currentNode)
            currentNode = next_father