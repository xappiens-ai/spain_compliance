/** Filas de un estado (balance o PyG) con todos los niveles, para exportar. */
export function aplanarEstado(nodos, profundidad = 0, salida = []) {
  const sangria = (n) => '  '.repeat(n)
  for (const nodo of nodos) {
    salida.push({
      codigo: nodo.code,
      concepto: `${sangria(profundidad)}${nodo.label}`,
      importes: nodo.importes,
    })
    if (nodo.hijos?.length) {
      aplanarEstado(nodo.hijos, profundidad + 1, salida)
      continue
    }
    for (const grupo of nodo.cuentas || []) {
      salida.push({
        codigo: grupo.codigo,
        concepto: `${sangria(profundidad + 1)}${grupo.nombre}`,
        importes: grupo.importes,
      })
      for (const sub of grupo.subcuentas) {
        salida.push({
          codigo: sub.numero,
          concepto: `${sangria(profundidad + 2)}${sub.nombre}`,
          importes: sub.importes,
        })
      }
    }
  }
  return salida
}

/** Nodo por código dentro de uno o varios árboles. */
export function buscarNodo(raices, code) {
  const pila = [...raices]
  while (pila.length) {
    const nodo = pila.shift()
    if (nodo.code === code) return nodo
    pila.unshift(...(nodo.hijos || []))
  }
  return null
}
