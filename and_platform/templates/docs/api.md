### Informasi Umum
Host yang digunakan untuk mengakses API platform adalah `https://and-be.idcyberskills.com`. Seluruh request dan response body API menggunakan format JSON. Pastikan Anda telah menyesuaikan konfigurasi dengan tepat.

### Submit Flags
API ini digunakan untuk melakukan submit atas flag yang berhasil dicuri dari diri sendiri ataupun tim lain. Perlu diingat kembali bahwa sebuah flag hanya berlaku pada tick tersebut.

Kirim POST-request ke endpoint `/api/v1/submit`. Body dari request haruslah memiliki format sebuah entri `flags` yang berisi array dari flag yang akan disubmit. Perlu diperhatikan bahwa maksimal 100 flag yang dapat disubmit dalam sebuah request. Autorisasi melalui JWT team diperlukan untuk dapat mengaksek API ini.

Contoh request:
```
curl -H 'Content-Type: application/json' -H 'Authorization: Bearer <team JWT>' \
    -X POST --data '{"flags": ["LKS{incorrect}", "LKS{expired}", "LKS{siwlzc8}", "LKS{siwlzc8}"]}' \
    https://and-be.idcyberskills.com/api/v1/submit
```

Contoh response:
```
{
    "data": [
        {
            "flag": "LKS{incorrect}",
            "verdict": "flag is wrong or expired."
        },
        {
            "flag": "LKS{expired}",
            "verdict": "flag is wrong or expired."
        },
        {
            "flag": "LKS{siwlzc8}",
            "verdict": "flag is correct."
        },
        {
            "flag": "LKS{siwlzc8}",
            "verdict": "flag already submitted."
        }
    ],
    "status": "success"
}
```

### List Challenges
API ini digunakan untuk melihat daftar challenge yang ada.

Kirim GET-request ke endpoint `/api/v1/challenges`.

Contoh request:
```
curl https://and-be.idcyberskills.com/api/v1/challenges
```

Contoh response:
```
{
    "data": [
        {
            "id": 1,
            "name": "Calc"
        },
        {
            "id": 2,
            "name": "Morse"
        }
    ],
    "status": "success"
}
```

### List Teams
API ini digunakan untuk melihat daftar team yang ada.

Kirim GET-request ke endpoint `/api/v1/teams`.

Contoh request:
```
curl https://and-be.idcyberskills.com/api/v1/teams
```

Contoh response:
```
{
    "data": [
        {
            "id": 10,
            "name": "Love of my life",
            "server": {
                "id": 1,
                "host": "10.0.1.101"
            }
        },
        {
            "id": 11,
            "name": "Easy come easy go",
            "server": {
                "id": 2,
                "host": "10.0.1.102"
            }
        }
    ],
    "status": "success"
}
```

### List Servers
API ini digunakan untuk melihat seluruh daftar alamat IP server yang dimiliki tiap tim. Alamat IP ini nantinya akan digunakan untuk melakukan attack.

Kirim GET-request ke endpoint `/api/v1/servers`.

Contoh request:
```
curl https://and-be.idcyberskills.com/api/v1/servers
```

Contoh response:
```
{
    "data": {
        // "1" dan "2" merupakan id team yang didapat dari API list teams
        "1": "10.0.1.101",
        "2": "10.0.1.102"
    },
    "status": "success"
}
```