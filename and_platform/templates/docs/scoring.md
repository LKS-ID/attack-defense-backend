Scoring dibagi menjadi dua, yaitu:
- Attack
- Defend

### Attack
Attack poin dalam satu tick dihitung dengan cara menjumlahkan nilai dari seluruh flag yang didapatkan pada tick tersebut. Terdapat dua jenis flag:
- Flag `ubuntu` bernilai 50 poin
- Flag `root` bernilai 100 poin

### Defense
Defense poin dalam satu tick dihitung dengan formula berikut:
```
(banyak up pada tick tersebut) * 90 - (banyak service faulty pada tick tersebut) + (100, jika flag tidak tercuri pada tick tersebut)
```

### Total Score
Total score adalah hasil penjumlahan attack dan defense poin pada seluruh tick.
