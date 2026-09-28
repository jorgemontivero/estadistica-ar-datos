# Pruebas de hipótesis

Nivel de significación: α = 0,05. Casos en la base: 150.

Cada prueba se eligió mirando los supuestos, no al revés. Al lado de cada una está la que se habría corrido con el otro supuesto, para que se vea cuándo la decisión importó.

> **Acá el supuesto decide la conclusión.** En Gasto mensual en materiales según grupo y Gasto mensual en materiales según nivel educativo la prueba que corresponde y la alternativa no coinciden en rechazar. En el resto de las comparaciones, discutir el supuesto no cambia lo que hay que escribir.

## Las pruebas

- **Edad (años) según grupo.** Prueba t de Welch para dos muestras, t(146,5) = -0,857, p = 0,393, d de Hedges = -0,140 (insignificante).
  Se eligió porque hay dos grupos y los dos pasan Shapiro-Wilk. La alternativa daba p = 0,499.
- **Ingreso mensual del hogar según grupo.** Mann-Whitney, U = 2.497, p = 0,355, r de rangos = 0,076 (insignificante).
  Se eligió porque hay dos grupos y alguno no pasa Shapiro-Wilk. La alternativa daba p = 0,280.
- **Puntaje de satisfacción según grupo.** Mann-Whitney, U = 1.778, p < 0,001, r de rangos = 0,315 (medio).
  Se eligió porque hay dos grupos y alguno no pasa Shapiro-Wilk. La alternativa daba p < 0,001.
- **Horas de estudio por semana según grupo.** Prueba t de Welch para dos muestras, t(147,3) = -2,523, p = 0,013, d de Hedges = -0,410 (chico).
  Se eligió porque hay dos grupos y los dos pasan Shapiro-Wilk. La alternativa daba p = 0,008.
- **Gasto mensual en materiales según grupo.** Mann-Whitney, U = 1.695, p < 0,001, r de rangos = 0,343 (medio).
  Se eligió porque hay dos grupos y alguno no pasa Shapiro-Wilk. La alternativa daba p = 0,625.
- **Sexo según grupo.** Prueba z para dos proporciones, o chi-cuadrado, χ²(1) = 4,933, p = 0,026, V de Cramér = 0,182 (chico).
  Se eligió porque todas las frecuencias esperadas llegan a 5. La alternativa daba p = 0,033.
- **Tiene beca según grupo.** Prueba exacta de Fisher, p = 1,000, V de Cramér = 0,032 (insignificante).
  Se eligió porque alguna frecuencia esperada es menor que 5, y la tabla es de 2×2. La alternativa daba p = 0,699.
- **Edad (años) según nivel educativo.** ANOVA de un factor, F(2; 146) = 0,002, p = 0,998, eta² = 0,000 (insignificante).
  Se eligió porque hay tres o más grupos, todos normales y con varianzas homogéneas. La alternativa daba p = 0,984.
- **Ingreso mensual del hogar según nivel educativo.** Kruskal-Wallis, H(2) = 2,531, p = 0,282, épsilon² = 0,004 (insignificante).
  Se eligió porque hay tres o más grupos y alguno no pasa Shapiro-Wilk. La alternativa daba p = 0,159.
- **Puntaje de satisfacción según nivel educativo.** Kruskal-Wallis, H(2) = 1,950, p = 0,377, épsilon² = 0,000 (insignificante).
  Se eligió porque hay tres o más grupos y alguno no pasa Shapiro-Wilk. La alternativa daba p = 0,283.
- **Horas de estudio por semana según nivel educativo.** ANOVA de un factor, F(2; 147) = 0,054, p = 0,947, eta² = 0,001 (insignificante).
  Se eligió porque hay tres o más grupos, todos normales y con varianzas homogéneas. La alternativa daba p = 0,875.
- **Gasto mensual en materiales según nivel educativo.** Kruskal-Wallis, H(2) = 7,026, p = 0,030, épsilon² = 0,034 (chico).
  Se eligió porque hay tres o más grupos y alguno no pasa Shapiro-Wilk. La alternativa daba p = 0,349.
- **Sexo según nivel educativo.** Chi-cuadrado de homogeneidad, χ²(2) = 1,242, p = 0,537, V de Cramér = 0,091 (insignificante).
  Se eligió porque todas las frecuencias esperadas llegan a 5.
- **Tiene beca según nivel educativo.** Chi-cuadrado de homogeneidad, χ²(2) = 0,522, p = 0,770, V de Cramér = 0,059 (insignificante).
  Se eligió porque alguna esperada es menor que 5, pero la tabla no es de 2×2.
