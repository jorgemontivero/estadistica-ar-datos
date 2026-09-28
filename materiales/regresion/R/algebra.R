# Resolver sistemas lineales, a mano y sin usar lm().
#
# Acá hay una decisión que conviene entender antes de usar el proyecto con
# datos propios.
#
# Un ajuste por mínimos cuadrados se puede resolver de varias maneras. `lm`
# usa una descomposición QR; numpy, por omisión, una SVD. Las dos son más
# estables que las **ecuaciones normales**, que es lo que hay acá: armar X'X,
# invertirla y multiplicar. Las ecuaciones normales elevan al cuadrado el
# número de condición del problema, así que con predictores muy
# correlacionados entre sí pierden precisión antes que las otras dos.
#
# Se usan igual, por una razón concreta: son **la única forma de que las dos
# versiones den exactamente lo mismo**. Con QR en R y SVD en Python, los
# coeficientes empiezan a diferir en el décimo dígito y los archivos dejan de
# ser idénticos. Escribir el solucionador una vez de cada lado resuelve eso.
#
# La defensa contra el problema de precisión no es teórica: el proyecto
# calcula el **VIF** de cada predictor y avisa cuando pasa de 10. Un VIF alto
# es exactamente la señal de que X'X está mal condicionada, y en ese caso el
# aviso dice que el modelo hay que repensarlo, no que el número esté un poco
# corrido.
#
# La inversa se calcula entera porque hace falta: los errores estándar de los
# coeficientes son la raíz de la diagonal de (X'X)⁻¹ multiplicada por la
# varianza residual.

# Inversa por Gauss-Jordan con pivoteo parcial.
#
# El pivoteo no es un adorno: sin él, un cero en la diagonal rompe la
# eliminación aunque la matriz sea perfectamente invertible.
invertir <- function(a) {
  n <- nrow(a)
  m <- cbind(a, diag(n))

  for (col in seq_len(n)) {
    # Pivoteo parcial: la fila con el valor absoluto más grande manda.
    candidatas <- col:n
    pivote <- candidatas[which.max(abs(m[candidatas, col]))]
    if (abs(m[pivote, col]) < 1e-12) return(NULL)  # singular
    if (pivote != col) {
      tmp <- m[col, ]
      m[col, ] <- m[pivote, ]
      m[pivote, ] <- tmp
    }

    m[col, ] <- m[col, ] / m[col, col]

    for (fila in seq_len(n)) {
      if (fila == col) next
      factor <- m[fila, col]
      if (factor != 0) m[fila, ] <- m[fila, ] - factor * m[col, ]
    }
  }

  m[, (n + 1):(2 * n), drop = FALSE]
}

# Mínimos cuadrados por ecuaciones normales: (X'X)⁻¹ X'y.
#
# Devuelve los coeficientes y la inversa, porque quien llama casi siempre
# necesita las dos cosas y calcular la inversa dos veces sería tonto.
resolver <- function(x, y) {
  xtx <- t(x) %*% x
  inversa <- invertir(xtx)
  if (is.null(inversa)) return(list(coeficientes = NULL, inversa = NULL))
  list(coeficientes = as.numeric(inversa %*% (t(x) %*% y)), inversa = inversa)
}

# El mismo ajuste con pesos, que es lo que cada paso del IRLS necesita.
#
# Equivale a multiplicar cada fila por la raíz de su peso, pero se arma
# directo X'WX para no recorrer los datos dos veces.
resolver_ponderado <- function(x, y, pesos) {
  xtw <- t(x * pesos)
  xtwx <- xtw %*% x
  inversa <- invertir(xtwx)
  if (is.null(inversa)) return(list(coeficientes = NULL, inversa = NULL))
  list(coeficientes = as.numeric(inversa %*% (xtw %*% y)), inversa = inversa)
}
