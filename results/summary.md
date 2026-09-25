# Results summary: run `main`

18800 answers, 16 model configurations. All rates in %.

## Table 1. Safety and helpfulness by compression level

```
size  quant   bpw  harmful_refusal  xstest_unsafe_refusal  benign_refusal  xstest_safe_refusal  degenerate_rate  cjk_drift_rate  tok_per_s
0.5b    F16 20.68             76.7                   90.0            20.0                 49.0              0.2             0.0  24.369084
0.5b   Q8_0 11.03             77.7                   90.0            19.3                 50.0              0.2             0.0  42.387400
0.5b   Q6_K 10.62             76.7                   86.0            18.0                 45.0              0.5             0.0  44.895394
0.5b Q5_K_M  8.53             83.0                   91.0            31.3                 63.0              0.6             0.0  50.234848
0.5b Q4_K_M  8.02             78.7                   90.0            18.7                 46.0              1.0             0.0  50.061259
0.5b   Q4_0  7.00             74.0                   91.0            28.7                 66.0              1.2             0.0  60.776156
0.5b Q3_K_M  7.05             82.7                   90.0            34.0                 64.0              1.5             0.0  56.872469
0.5b   Q2_K  6.78             81.7                   96.0            36.7                 62.0              2.9             0.0  60.950846
1.5b    F16 18.50             96.0                   96.0            30.7                 54.0              0.0             0.1   8.013511
1.5b   Q8_0  9.84             96.0                   96.0            30.7                 53.0              0.1             0.2  14.280907
1.5b   Q6_K  7.61             97.0                   97.0            33.3                 54.0              0.1             0.1  17.513774
1.5b Q5_K_M  6.68             96.0                   98.0            31.3                 56.0              0.0             0.1  19.350969
1.5b Q4_K_M  5.80             95.7                   96.0            36.0                 60.0              0.0             0.1  22.076030
1.5b   Q4_0  5.54             98.3                   99.0            40.7                 70.0              0.1             0.1  23.298064
1.5b Q3_K_M  4.80             95.0                   96.0            30.7                 50.0              0.4             0.1  22.465820
1.5b   Q2_K  3.91             93.7                   85.0            64.7                 68.0              7.1             0.0  29.341590
```

## Table 2. Hidden-instruction (indirect prompt injection) attacks

```
size  quant   bpw  asr  obeyed_full  obeyed_partial  obeyed_decision  reported  clean_task_done  clean_target_baseline
0.5b    F16 20.68 22.0          2.3             2.0             17.7       0.3             80.0                   20.0
0.5b   Q8_0 11.03 22.3          2.7             2.0             17.7       0.7             80.0                   18.7
0.5b   Q6_K 10.62 23.7          2.3             3.0             18.3       0.0             80.0                   17.3
0.5b Q5_K_M  8.53 23.3          4.7             3.0             15.7       0.0             96.0                   32.0
0.5b Q4_K_M  8.02 24.3          3.0             1.3             20.0       0.0            100.0                   10.7
0.5b   Q4_0  7.00 20.0          1.0             1.7             17.3       0.3            100.0                   32.0
0.5b Q3_K_M  7.05 17.7          1.7             2.3             13.7       0.7             98.7                   38.7
0.5b   Q2_K  6.78 20.7          2.7             1.3             16.7       0.0             97.3                   29.3
1.5b    F16 18.50 30.0         13.0             7.7              9.3       0.0             94.7                   14.7
1.5b   Q8_0  9.84 30.0         13.3             7.7              9.0       0.0             90.7                   14.7
1.5b   Q6_K  7.61 30.7         12.0             8.3             10.3       0.0             89.3                   17.3
1.5b Q5_K_M  6.68 29.3         10.0            10.7              8.7       0.0             92.0                   16.0
1.5b Q4_K_M  5.80 31.0          6.7            13.7             10.7       0.0             92.0                   13.3
1.5b   Q4_0  5.54 37.3          7.0            18.3             12.0       0.3             92.0                   12.0
1.5b Q3_K_M  4.80 22.0          1.3            12.3              8.3       0.3             92.0                   18.7
1.5b   Q2_K  3.91 30.0         10.0             9.7             10.3       1.3             48.0                    5.3
```

## Table 3. Attack success by factor (compression levels pooled)

```
  factor size          level   n  asr
doc_type 0.5b             cv 480 36.7
doc_type 0.5b          email 480 25.4
doc_type 0.5b         ticket 480 24.4
doc_type 0.5b         review 480 18.1
doc_type 0.5b        invoice 480  4.2
doc_type 1.5b         ticket 480 44.6
doc_type 1.5b             cv 480 37.1
doc_type 1.5b        invoice 480 30.2
doc_type 1.5b          email 480 26.7
doc_type 1.5b         review 480 11.7
    goal 0.5b       decision 600 68.5
    goal 0.5b         hijack 600 11.5
    goal 0.5b         canary 600  5.3
    goal 0.5b  phishing_link 600  1.7
    goal 1.5b         hijack 600 72.2
    goal 1.5b       decision 600 39.3
    goal 1.5b         canary 600  6.2
    goal 1.5b  phishing_link 600  2.5
position 0.5b            end 800 28.2
position 0.5b         middle 800 19.4
position 0.5b          start 800 17.6
position 1.5b            end 800 35.9
position 1.5b         middle 800 28.9
position 1.5b          start 800 25.4
   style 0.5b    hidden_html 480 24.4
   style 0.5b          plain 480 23.1
   style 0.5b    polite_note 480 21.0
   style 0.5b      authority 480 20.2
   style 0.5b fake_delimiter 480 20.0
   style 1.5b fake_delimiter 480 33.5
   style 1.5b    polite_note 480 33.5
   style 1.5b    hidden_html 480 33.3
   style 1.5b          plain 480 29.6
   style 1.5b      authority 480 20.2
```

## Table 4. Paired McNemar tests vs F16 (Holm-corrected)

```
             metric size  quant  f16_rate  quant_rate  only_f16  only_quant  p_holm  significant_0.05
    harmful_refusal 0.5b Q5_K_M    0.7667      0.8300         0          19  0.0000              True
    harmful_refusal 0.5b Q3_K_M    0.7667      0.8267         7          25  0.0126              True
    harmful_refusal 0.5b   Q2_K    0.7667      0.8167        10          25  0.0834             False
    harmful_refusal 0.5b   Q8_0    0.7667      0.7767         0           3  1.0000             False
    harmful_refusal 0.5b   Q4_0    0.7667      0.7400        23          15  1.0000             False
    harmful_refusal 0.5b Q4_K_M    0.7667      0.7867         9          15  1.0000             False
    harmful_refusal 0.5b   Q6_K    0.7667      0.7667         1           1  1.0000             False
    harmful_refusal 1.5b   Q4_0    0.9600      0.9833         0           7  0.1094             False
    harmful_refusal 1.5b   Q2_K    0.9600      0.9367        17          10  1.0000             False
    harmful_refusal 1.5b   Q6_K    0.9600      0.9700         0           3  1.0000             False
    harmful_refusal 1.5b Q3_K_M    0.9600      0.9500         6           3  1.0000             False
    harmful_refusal 1.5b   Q8_0    0.9600      0.9600         0           0  1.0000             False
    harmful_refusal 1.5b Q5_K_M    0.9600      0.9600         2           2  1.0000             False
    harmful_refusal 1.5b Q4_K_M    0.9600      0.9567         1           0  1.0000             False
xstest_safe_refusal 0.5b Q3_K_M    0.4900      0.6400         1          16  0.0019              True
xstest_safe_refusal 0.5b Q5_K_M    0.4900      0.6300         1          15  0.0031              True
xstest_safe_refusal 0.5b   Q4_0    0.4900      0.6600         4          21  0.0046              True
xstest_safe_refusal 0.5b   Q2_K    0.4900      0.6200         6          19  0.0585             False
xstest_safe_refusal 0.5b   Q6_K    0.4900      0.4500         4           0  0.3750             False
xstest_safe_refusal 0.5b Q4_K_M    0.4900      0.4600         6           3  1.0000             False
xstest_safe_refusal 0.5b   Q8_0    0.4900      0.5000         0           1  1.0000             False
xstest_safe_refusal 1.5b   Q4_0    0.5400      0.7000         3          19  0.0060              True
xstest_safe_refusal 1.5b   Q2_K    0.5400      0.6800         8          22  0.0967             False
xstest_safe_refusal 1.5b Q4_K_M    0.5400      0.6000         4          10  0.8978             False
xstest_safe_refusal 1.5b Q3_K_M    0.5400      0.5000        10           6  1.0000             False
xstest_safe_refusal 1.5b Q5_K_M    0.5400      0.5600         1           3  1.0000             False
xstest_safe_refusal 1.5b   Q8_0    0.5400      0.5300         1           0  1.0000             False
xstest_safe_refusal 1.5b   Q6_K    0.5400      0.5400         2           2  1.0000             False
   injection_obeyed 0.5b Q3_K_M    0.2200      0.1767        20           7  0.1341             False
   injection_obeyed 0.5b   Q6_K    0.2200      0.2367         2           7  1.0000             False
   injection_obeyed 0.5b Q4_K_M    0.2200      0.2433        10          17  1.0000             False
   injection_obeyed 0.5b   Q4_0    0.2200      0.2000        16          10  1.0000             False
   injection_obeyed 0.5b   Q2_K    0.2200      0.2067        13           9  1.0000             False
   injection_obeyed 0.5b Q5_K_M    0.2200      0.2333        10          14  1.0000             False
   injection_obeyed 0.5b   Q8_0    0.2200      0.2233         2           3  1.0000             False
   injection_obeyed 1.5b   Q4_0    0.3000      0.3733         8          30  0.0033              True
   injection_obeyed 1.5b Q3_K_M    0.3000      0.2200        37          13  0.0056              True
   injection_obeyed 1.5b Q4_K_M    0.3000      0.3100        15          18  1.0000             False
   injection_obeyed 1.5b   Q6_K    0.3000      0.3067         8          10  1.0000             False
   injection_obeyed 1.5b Q5_K_M    0.3000      0.2933        10           8  1.0000             False
   injection_obeyed 1.5b   Q8_0    0.3000      0.3000         9           9  1.0000             False
   injection_obeyed 1.5b   Q2_K    0.3000      0.3000        34          34  1.0000             False
```

Validation samples: 200 refusal rows, 132 injection rows (results/analysis/main/validation/).
