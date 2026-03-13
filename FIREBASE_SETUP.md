# 🔥 Guia de Configuração do Firebase — PyAds

Este guia explica passo a passo como criar e configurar o projeto Firebase para o PyAds funcionar.

---

## Passo 1 — Criar projeto no Firebase

1. Acesse **[console.firebase.google.com](https://console.firebase.google.com)**
2. Clique em **"Adicionar projeto"**
3. Dê um nome (ex: `pyads-producao`)
4. Pode desativar o Google Analytics (opcional)
5. Clique em **"Criar projeto"** e aguarde

---

## Passo 2 — Configurar Authentication

1. No menu lateral, clique em **"Build" → "Authentication"**
2. Clique em **"Começar"**
3. Na aba **"Sign-in method"**, clique em **"E-mail/senha"**
4. Ative a primeira opção e clique **"Salvar"**

### Criar usuário administrador
1. Vá na aba **"Users"**
2. Clique em **"Adicionar usuário"**
3. Preencha o e-mail e senha do administrador
4. Clique **"Adicionar usuário"**

---

## Passo 3 — Configurar Realtime Database

1. No menu lateral, clique em **"Build" → "Realtime Database"**
2. Clique em **"Criar banco de dados"**
3. Escolha a localização (recomendado: `us-central1`)
4. Selecione **"Iniciar no modo de teste"** (vamos configurar as regras depois)
5. Clique em **"Habilitar"**

### Aplicar regras de segurança
1. Clique na aba **"Regras"**
2. Substitua o conteúdo pelo seguinte:

```json
{
  "rules": {
    "anuncios": {
      ".read": "auth != null",
      ".write": "auth != null"
    },
    "playlists": {
      ".read": "auth != null",
      ".write": "auth != null"
    },
    "players": {
      ".read": "auth != null",
      "$playerId": {
        ".write": "auth != null"
      }
    },
    "logs": {
      ".read": "auth != null",
      ".write": "auth != null"
    }
  }
}
```

3. Clique em **"Publicar"**

---

## Passo 4 — Configurar Storage

1. No menu lateral, clique em **"Build" → "Storage"**
2. Clique em **"Começar"**
3. Selecione **"Iniciar no modo de teste"**
4. Escolha a localização (mesma do banco de dados)
5. Clique em **"Avançar"** e depois **"Concluído"**

### Aplicar regras do Storage
1. Clique na aba **"Regras"**
2. Substitua o conteúdo pelo seguinte:

```
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    match /audios/{allPaths=**} {
      allow read: if request.auth != null;
      allow write: if request.auth != null
                   && request.resource.size < 50 * 1024 * 1024
                   && (request.resource.contentType.matches('audio/.*'));
    }
  }
}
```

3. Clique em **"Publicar"**

---

## Passo 5 — Obter credenciais para o Painel Web (React)

1. No menu lateral, clique na ⚙️ **engrenagem** → **"Configurações do projeto"**
2. Role até a seção **"Seus apps"**
3. Clique em **"Adicionar app"** → escolha o ícone **"Web" (</>)**
4. Dê um apelido (ex: `pyads-web`) e clique **"Registrar app"**
5. Você verá o objeto `firebaseConfig`. Copie-o completo:

```javascript
const firebaseConfig = {
  apiKey: "AIzaSy...",
  authDomain: "pyads-producao.firebaseapp.com",
  databaseURL: "https://pyads-producao-default-rtdb.firebaseio.com",
  projectId: "pyads-producao",
  storageBucket: "pyads-producao.appspot.com",
  messagingSenderId: "123456789",
  appId: "1:123456789:web:abc123"
};
```

6. Abra o arquivo **`src/firebase.js`** no projeto React
7. Substitua o `firebaseConfig` existente pelo seu

---

## Passo 6 — Obter credenciais para o Player Python

1. Ainda nas **"Configurações do projeto"**
2. Clique na aba **"Contas de serviço"**
3. Clique em **"Gerar nova chave privada"**
4. Confirme e o arquivo JSON será baixado
5. Renomeie para **`serviceAccountKey.json`**
6. Mova para a pasta **`python/`** do projeto PyAds

---

## Passo 7 — Configurar o Player Python

Edite o arquivo **`python/pyads_config.json`** (criado na primeira execução):

```json
{
  "firebase_credentials": "serviceAccountKey.json",
  "firebase_database_url": "https://SEU-PROJETO-default-rtdb.firebaseio.com",
  "firebase_storage_bucket": "SEU-PROJETO.appspot.com",
  "player_id": "player_loja_01",
  "player_nome": "Player Loja Principal",
  "volume_durante_anuncio": 100,
  "volume_outros_apps": 10
}
```

> ⚠️ O `player_id` deve ser **único** para cada computador onde o player for instalado

---

## Passo 8 — Instalar e rodar o Painel Web

```bash
# Na pasta pyads-react/
npm install
npm start
```

O painel abrirá em `http://localhost:3000`

### Deploy no Firebase Hosting (opcional)
```bash
npm install -g firebase-tools
firebase login
firebase init hosting   # selecione o projeto criado, pasta: build
npm run build
firebase deploy --only hosting
```

---

## Passo 9 — Instalar e rodar o Player Python

```bash
# Na pasta python/
pip install -r requirements.txt
python player.py
```

---

## Resumo das URLs importantes

| Item | Onde encontrar |
|------|---------------|
| `databaseURL` | Console → Realtime Database → URL no topo (termina com `.firebaseio.com`) |
| `storageBucket` | Console → Storage → URL no topo (termina com `.appspot.com`) |
| `apiKey`, `projectId`, etc. | Console → Configurações → Seus apps → Web |
| `serviceAccountKey.json` | Console → Configurações → Contas de serviço → Gerar chave |

---

## ❓ Problemas comuns

### "Permission denied" no banco de dados
- Verifique se as **regras** foram publicadas corretamente no passo 3
- Confirme que o usuário está **logado** no painel antes de ler/escrever

### Upload de áudio falha
- Verifique as **regras do Storage** (passo 4)
- O arquivo deve ser menor que **50 MB**
- Apenas formatos **MP3 ou WAV** são aceitos

### Player Python não aparece como "Online" no painel
- Verifique se o `firebase_database_url` no `pyads_config.json` está correto
- Certifique-se que o `serviceAccountKey.json` está na pasta `python/`
- Verifique a conexão com a internet do computador onde o player está rodando

### "serviceAccountKey.json não encontrado"
- O arquivo deve estar na **mesma pasta** que o `player.py`
- Certifique-se que foi gerado na aba **"Contas de serviço"** e não no app Web

---

## 🔒 Segurança em produção

Antes de lançar em produção, considere:

1. **Restringir a API Key** do projeto Web no Google Cloud Console
2. **Não versionar** o `serviceAccountKey.json` (adicione ao `.gitignore`)
3. **Não versionar** o `pyads_config.json` se contiver dados sensíveis
4. **Rever as regras** do banco e storage para permitir apenas as operações necessárias
