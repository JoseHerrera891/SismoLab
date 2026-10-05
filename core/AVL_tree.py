
class AVLnode:
    """Represents a node in the AVL tree holding a seismic Event."""
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
        """Returns the event's key K = (P, M, I) for BST comparisons."""
        return self.value.key


class AVLtree:
    """AVL Tree matching instructor's base implementation."""
    def __init__(self):
        self.raiz = None
        
        # Metrics tracking required by Section 14
        self.ll_rotations = 0
        self.rr_rotations = 0
        self.lr_rotations = 0
        self.rl_rotations = 0

    # --------------------------------------------------
    # ALTURA Y FACTOR DE BALANCE
    # --------------------------------------------------
    def _height(self, node):
        if node is None:
            return -1
        return node.getHeight()

    def _update_height(self, nodo):
        if nodo is not None:
            leftHeight = self._height(nodo.getLeftChild())
            rightHeight = self._height(nodo.getRightChild())
            nodo.setHeight(1 + max(leftHeight, rightHeight))

    def _get_balance_factor(self, nodo):
        if nodo is None:
            return 0
        return self._height(nodo.getLeftChild()) - self._height(nodo.getRightChild())

    # --------------------------------------------------
    # ROTACIONES / GIROS (Adaptados del profesor)
    # --------------------------------------------------
    def _rotate_right(self, superior):
        """Single right rotation (LL)."""
        mitad = superior.getLeftChild()
        aux = mitad.getRightChild()

        if aux is not None:
            aux.setFather(superior)

        mitad.setRightChild(superior)
        superior.setLeftChild(aux)

        padre_superior = superior.getFather()
        mitad.setFather(padre_superior)
        superior.setFather(mitad)

        if padre_superior is None:
            self.raiz = mitad
        elif padre_superior.getLeftChild() == superior:
            padre_superior.setLeftChild(mitad)
        else:
            padre_superior.setRightChild(mitad)

        self._update_height(superior)
        self._update_height(mitad)
        return mitad

    def _rotate_left(self, superior):
        """Single left rotation (RR)."""
        mitad = superior.getRightChild()
        aux = mitad.getLeftChild()

        if aux is not None:
            aux.setFather(superior)

        mitad.setLeftChild(superior)
        superior.setRightChild(aux)

        padre_superior = superior.getFather()
        mitad.setFather(padre_superior)
        superior.setFather(mitad)

        if padre_superior is None:
            self.raiz = mitad
        elif padre_superior.getLeftChild() == superior:
            padre_superior.setLeftChild(mitad)
        else:
            padre_superior.setRightChild(mitad)

        self._update_height(superior)
        self._update_height(mitad)
        return mitad

    # --------------------------------------------------
    # INSERTAR
    # --------------------------------------------------
    def insert(self, event, auto_balance: bool = True):
        nodo = AVLnode(event)
        if self.raiz is None:
            self.raiz = nodo
            nodo.setFather(None)
        else:
            self._insert(nodo, self.raiz, auto_balance)

    def _insert(self, nodo, raizActual, auto_balance: bool):
        if raizActual.key == nodo.key:
            return  # Clave duplicada

        if nodo.key < raizActual.key:
            izq = raizActual.getLeftChild()
            if izq is None:
                raizActual.setLeftChild(nodo)
                nodo.setFather(raizActual)
            else:
                self._insert(nodo, izq, auto_balance)
        else:
            der = raizActual.getRightChild()
            if der is None:
                raizActual.setRightChild(nodo)
                nodo.setFather(raizActual)
            else:
                self._insert(nodo, der, auto_balance)

        self._update_height(raizActual)

        if auto_balance:
            self._rebalance_node(raizActual)

    # --------------------------------------------------
    # BUSCAR Y ELIMINAR (Basado en la plantilla)
    # --------------------------------------------------
    def search_by_key(self, key_tuple):
        if self.raiz is None:
            return None
        return self._search(key_tuple, self.raiz)

    def _search(self, key_tuple, raizActual):
        if raizActual is None:
            return None
        if key_tuple == raizActual.key:
            return raizActual
        if key_tuple < raizActual.key:
            return self._search(key_tuple, raizActual.getLeftChild())
        return self._search(key_tuple, raizActual.getRightChild())

    def delete(self, key_tuple, auto_balance: bool = True):
        nodo = self.search_by_key(key_tuple)
        if nodo is not None:
            self._delete(nodo, auto_balance)

    def _delete(self, nodo, auto_balance: bool):
        padre = nodo.getFather()

        # CASO 1: Es una hoja
        if nodo.getLeftChild() is None and nodo.getRightChild() is None:
            if padre is None:
                self.raiz = None
            elif padre.getLeftChild() == nodo:
                padre.setLeftChild(None)
            else:
                padre.setRightChild(None)
            nodo.setFather(None)
            if auto_balance and padre:
                self._rebalance_ancestors(padre)
            return

        # CASO 2A: Solo hijo derecho
        if nodo.getLeftChild() is None:
            hijo = nodo.getRightChild()
            if padre is None:
                self.raiz = hijo
                hijo.setFather(None)
            else:
                if padre.getLeftChild() == nodo:
                    padre.setLeftChild(hijo)
                else:
                    padre.setRightChild(hijo)
                hijo.setFather(padre)
            if auto_balance and padre:
                self._rebalance_ancestors(padre)
            return

        # CASO 2B: Solo hijo izquierdo
        if nodo.getRightChild() is None:
            hijo = nodo.getLeftChild()
            if padre is None:
                self.raiz = hijo
                hijo.setFather(None)
            else:
                if padre.getLeftChild() == nodo:
                    padre.setLeftChild(hijo)
                else:
                    padre.setRightChild(hijo)
                hijo.setFather(padre)
            if auto_balance and padre:
                self._rebalance_ancestors(padre)
            return

        # CASO 3: Dos hijos (Usa el PREDECESOR como en la plantilla del profesor)
        predecessor = self._get_predecessor(nodo)
        nodo.setValue(predecessor.getValue())
        self._delete(predecessor, auto_balance)

    def _get_predecessor(self, nodo):
        actual = nodo.getLeftChild()
        while actual.getRightChild() is not None:
            actual = actual.getRightChild()
        return actual

    # --------------------------------------------------
    # CONTROL DE BALANCEO
    # --------------------------------------------------
    def _rebalance_node(self, nodo):
        fb = self._get_balance_factor(nodo)
        
        # Caso LL
        if fb > 1 and self._get_balance_factor(nodo.getLeftChild()) >= 0:
            self.ll_rotations += 1
            return self._rotate_right(nodo)

        # Caso LR
        if fb > 1 and self._get_balance_factor(nodo.getLeftChild()) < 0:
            self.lr_rotations += 1
            nodo.setLeftChild(self._rotate_left(nodo.getLeftChild()))
            return self._rotate_right(nodo)

        # Caso RR
        if fb < -1 and self._get_balance_factor(nodo.getRightChild()) <= 0:
            self.rr_rotations += 1
            return self._rotate_left(nodo)

        # Caso RL
        if fb < -1 and self._get_balance_factor(nodo.getRightChild()) > 0:
            self.rl_rotations += 1
            nodo.setRightChild(self._rotate_right(nodo.getRightChild()))
            return self._rotate_left(nodo)

        return nodo

    def _rebalance_ancestors(self, nodo):
        actual = nodo
        while actual is not None:
            self._update_height(actual)
            siguiente_padre = actual.getFather()
            self._rebalance_node(actual)
            actual = siguiente_padre