
class AVLnode:
    """Represents a node in the AVL tree holding a seismic Event."""
    def __init__(self, evento):#cambiar a event
        self.valor = evento  # Contiene el objeto Event # cambiar a value
        self.altura = 0 #cambiar a height
        self.hijoIzquierdo = None #cambiar a leftChild
        self.hijoDerecho = None #cambiar a rightChild
        self.padre = None #father

    def getValor(self):
        return self.valor

    def setValor(self, valor): 
        self.valor = valor

    def getHijoIzquierdo(self):
        return self.hijoIzquierdo

    def setHijoIzquierdo(self, nodo):
        self.hijoIzquierdo = nodo

    def getHijoDerecho(self):
        return self.hijoDerecho

    def setHijoDerecho(self, nodo):
        self.hijoDerecho = nodo

    def getPadre(self):
        return self.padre

    def setPadre(self, nodo):
        self.padre = nodo

    def getAltura(self):
        return self.altura

    def setAltura(self, h):
        self.altura = h

    @property
    def key(self) -> tuple:
        """Returns the event's key K = (P, M, I) for BST comparisons."""
        return self.valor.key


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
    def _altura(self, nodo):
        if nodo is None:
            return -1
        return nodo.getAltura()

    def _actualizarAltura(self, nodo):
        if nodo is not None:
            alturaIzq = self._altura(nodo.getHijoIzquierdo())
            alturaDer = self._altura(nodo.getHijoDerecho())
            nodo.setAltura(1 + max(alturaIzq, alturaDer))

    def _get_balance_factor(self, nodo):
        if nodo is None:
            return 0
        return self._altura(nodo.getHijoIzquierdo()) - self._altura(nodo.getHijoDerecho())

    # --------------------------------------------------
    # ROTACIONES / GIROS (Adaptados del profesor)
    # --------------------------------------------------
    def _giroSimpleDerecha(self, superior):
        """Single right rotation (LL)."""
        mitad = superior.getHijoIzquierdo()
        aux = mitad.getHijoDerecho()

        if aux is not None:
            aux.setPadre(superior)

        mitad.setHijoDerecho(superior)
        superior.setHijoIzquierdo(aux)

        padre_superior = superior.getPadre()
        mitad.setPadre(padre_superior)
        superior.setPadre(mitad)

        if padre_superior is None:
            self.raiz = mitad
        elif padre_superior.getHijoIzquierdo() == superior:
            padre_superior.setHijoIzquierdo(mitad)
        else:
            padre_superior.setHijoDerecho(mitad)

        self._actualizarAltura(superior)
        self._actualizarAltura(mitad)
        return mitad

    def _giroSimpleIzquierda(self, superior):
        """Single left rotation (RR)."""
        mitad = superior.getHijoDerecho()
        aux = mitad.getHijoIzquierdo()

        if aux is not None:
            aux.setPadre(superior)

        mitad.setHijoIzquierdo(superior)
        superior.setHijoDerecho(aux)

        padre_superior = superior.getPadre()
        mitad.setPadre(padre_superior)
        superior.setPadre(mitad)

        if padre_superior is None:
            self.raiz = mitad
        elif padre_superior.getHijoIzquierdo() == superior:
            padre_superior.setHijoIzquierdo(mitad)
        else:
            padre_superior.setHijoDerecho(mitad)

        self._actualizarAltura(superior)
        self._actualizarAltura(mitad)
        return mitad

    # --------------------------------------------------
    # INSERTAR
    # --------------------------------------------------
    def insertar(self, evento, auto_balance: bool = True):
        nodo = AVLnode(evento)
        if self.raiz is None:
            self.raiz = nodo
            nodo.setPadre(None)
        else:
            self._insertar(nodo, self.raiz, auto_balance)

    def _insertar(self, nodo, raizActual, auto_balance: bool):
        if raizActual.key == nodo.key:
            return  # Clave duplicada

        if nodo.key < raizActual.key:
            izq = raizActual.getHijoIzquierdo()
            if izq is None:
                raizActual.setHijoIzquierdo(nodo)
                nodo.setPadre(raizActual)
            else:
                self._insertar(nodo, izq, auto_balance)
        else:
            der = raizActual.getHijoDerecho()
            if der is None:
                raizActual.setHijoDerecho(nodo)
                nodo.setPadre(raizActual)
            else:
                self._insertar(nodo, der, auto_balance)

        self._actualizarAltura(raizActual)

        if auto_balance:
            self._verificar_y_balancear_nodo(raizActual)

    # --------------------------------------------------
    # BUSCAR Y ELIMINAR (Basado en la plantilla)
    # --------------------------------------------------
    def buscar_por_clave(self, key_tuple):
        if self.raiz is None:
            return None
        return self._buscar(key_tuple, self.raiz)

    def _buscar(self, key_tuple, raizActual):
        if raizActual is None:
            return None
        if key_tuple == raizActual.key:
            return raizActual
        if key_tuple < raizActual.key:
            return self._buscar(key_tuple, raizActual.getHijoIzquierdo())
        return self._buscar(key_tuple, raizActual.getHijoDerecho())

    def eliminar(self, key_tuple, auto_balance: bool = True):
        nodo = self.buscar_por_clave(key_tuple)
        if nodo is not None:
            self._eliminar(nodo, auto_balance)

    def _eliminar(self, nodo, auto_balance: bool):
        padre = nodo.getPadre()

        # CASO 1: Es una hoja
        if nodo.getHijoIzquierdo() is None and nodo.getHijoDerecho() is None:
            if padre is None:
                self.raiz = None
            elif padre.getHijoIzquierdo() == nodo:
                padre.setHijoIzquierdo(None)
            else:
                padre.setHijoDerecho(None)
            nodo.setPadre(None)
            if auto_balance and padre:
                self._revisar_balanceo_ascendente(padre)
            return

        # CASO 2A: Solo hijo derecho
        if nodo.getHijoIzquierdo() is None:
            hijo = nodo.getHijoDerecho()
            if padre is None:
                self.raiz = hijo
                hijo.setPadre(None)
            else:
                if padre.getHijoIzquierdo() == nodo:
                    padre.setHijoIzquierdo(hijo)
                else:
                    padre.setHijoDerecho(hijo)
                hijo.setPadre(padre)
            if auto_balance and padre:
                self._revisar_balanceo_ascendente(padre)
            return

        # CASO 2B: Solo hijo izquierdo
        if nodo.getHijoDerecho() is None:
            hijo = nodo.getHijoIzquierdo()
            if padre is None:
                self.raiz = hijo
                hijo.setPadre(None)
            else:
                if padre.getHijoIzquierdo() == nodo:
                    padre.setHijoIzquierdo(hijo)
                else:
                    padre.setHijoDerecho(hijo)
                hijo.setPadre(padre)
            if auto_balance and padre:
                self._revisar_balanceo_ascendente(padre)
            return

        # CASO 3: Dos hijos (Usa el PREDECESOR como en la plantilla del profesor)
        predecesor = self._getPredecesor(nodo)
        nodo.setValor(predecesor.getValor())
        self._eliminar(predecesor, auto_balance)

    def _getPredecesor(self, nodo):
        actual = nodo.getHijoIzquierdo()
        while actual.getHijoDerecho() is not None:
            actual = actual.getHijoDerecho()
        return actual

    # --------------------------------------------------
    # CONTROL DE BALANCEO
    # --------------------------------------------------
    def _verificar_y_balancear_nodo(self, nodo):
        fb = self._get_balance_factor(nodo)
        
        # Caso LL
        if fb > 1 and self._get_balance_factor(nodo.getHijoIzquierdo()) >= 0:
            self.ll_rotations += 1
            return self._giroSimpleDerecha(nodo)

        # Caso LR
        if fb > 1 and self._get_balance_factor(nodo.getHijoIzquierdo()) < 0:
            self.lr_rotations += 1
            nodo.setHijoIzquierdo(self._giroSimpleIzquierda(nodo.getHijoIzquierdo()))
            return self._giroSimpleDerecha(nodo)

        # Caso RR
        if fb < -1 and self._get_balance_factor(nodo.getHijoDerecho()) <= 0:
            self.rr_rotations += 1
            return self._giroSimpleIzquierda(nodo)

        # Caso RL
        if fb < -1 and self._get_balance_factor(nodo.getHijoDerecho()) > 0:
            self.rl_rotations += 1
            nodo.setHijoDerecho(self._giroSimpleDerecha(nodo.getHijoDerecho()))
            return self._giroSimpleIzquierda(nodo)

        return nodo

    def _revisar_balanceo_ascendente(self, nodo):
        actual = nodo
        while actual is not None:
            self._actualizarAltura(actual)
            siguiente_padre = actual.getPadre()
            self._verificar_y_balancear_nodo(actual)
            actual = siguiente_padre