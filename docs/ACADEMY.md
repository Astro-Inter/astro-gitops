# CD no AWS Academy — SCRUM-393

Fluxo: push/merge na main da astro-ai-api → testes → imagem GHCR com SHA →
branch no astro-gitops → PR → aprovação e merge na main → Argo CD → EKS.

Os manifestos Academy são mantidos somente neste repositório central.
O GITHUB_TOKEN da API publica no GHCR; ASTRO_GITOPS_TOKEN propõe a tag
aqui numa branch e abre PR. Nenhuma chave AWS é usada no workflow. PRs da API executam apenas
validação, sem publicar imagens nem modificar o GitOps.

## Permissão entre repositórios

Antes de fazer merge da nova PR na astro-ai-api:

1. Crie um token fine-grained no GitHub, com expiração curta (ex.: 30 dias).
   Resource owner: Astro-Inter. Repository access: Only select repositories,
   selecionando SOMENTE astro-gitops. Repository permissions: Contents e Pull requests
   Read and write; Metadata Read é automática. Não dê acesso a workflows,
   administração, outros repositórios ou AWS. Se a organização exigir
   aprovação, aguarde o token ser aprovado.
2. Na astro-ai-api, Settings → Secrets and variables → Actions →
   New repository secret: nome ASTRO_GITOPS_TOKEN, valor do token.
   Nunca envie o token pelo chat ou faça commit dele.
3. Esse token é DIFERENTE do PAT classic read:packages que o Kubernetes usa.
   Renove o Secret do Actions quando expirar. GITHUB_TOKEN sozinho não escreve
   em outro repositório. Para uma integração duradoura, prefira GitHub App.
   Documentação: https://docs.github.com/en/actions/tutorials/authenticate-with-github_token
4. A main é protegida, inclusive para administradores. Toda atualização exige
   PR, uma aprovação de outra pessoa, check validate, branch atualizada e
   conversas resolvidas. Novos commits invalidam aprovações anteriores.
   Não remova nem contorne proteções. Não há merge automático.
5. Tokens limitados ao repositório antigo precisam ser recriados/ajustados:
   o nome é igual, mas o GitHub considera este um novo repositório.

## Antes do primeiro deploy

1. Aprovar e fazer merge da PR de configuração inicial deste repo.
   Depois configurar o token, fazer merge da PR #11 da API e aguardar validate,
   publish e update-gitops. Aprovar e fazer merge da PR de tag aberta pela
   automação neste repo. Confirmar a tag aprovada em
   apps/astro-ai-api/overlays/academy/kustomization.yaml na main.
   Nenhuma branch GitOps é criada na API: Argo acompanha a main deste repo.
   A tag inicial já corresponde à imagem que foi publicada manualmente;
   ela serve como ponto de partida, não como confirmação de deploy.
2. Confirmar que o contexto do CloudShell aponta para `CD-Astro`:

```bash
aws eks update-kubeconfig --region us-east-1 --name CD-Astro
kubectl config current-context
kubectl get nodes
kubectl create namespace astro-ai --dry-run=client -o yaml | kubectl apply -f -
```

3. Criar um PAT classic do GitHub com **somente `read:packages`**, expiração
   curta e acesso ao pacote privado `Astro-Inter/astro-ai-api`. Autorizar SSO
   se exigido. O PAT de leitura NÃO é o token usado pelo workflow para escrita.
   No Bash do CloudShell, leia o token sem exibi-lo nem gravá-lo literalmente
   no histórico (não compartilhe capturas enquanto manipula credenciais):

```bash
read -rp 'Usuário GitHub: ' GHCR_USER
read -rsp 'Token GHCR somente leitura: ' GHCR_READ_TOKEN
printf '\n'
kubectl -n astro-ai create secret docker-registry ghcr-read \
  --docker-server=ghcr.io --docker-username="$GHCR_USER" \
  --docker-password="$GHCR_READ_TOKEN" --dry-run=client -o yaml \
  | kubectl apply -f -
unset GHCR_READ_TOKEN GHCR_USER
```

Renove esse Secret quando o token expirar. Não salve nem versione seu valor.

4. Prepare um arquivo LOCAL `secrets.env`, seguindo
   `apps/astro-ai-api/secrets.env.example`. Use valores reais, sem aspas externas,
   sem `export`, sem múltiplas linhas e sem expansão de variáveis. Inclua as
   credenciais dos serviços externos e `A2A_SHARED_TOKEN` com pelo menos 32
   caracteres; `MONGODB_DATABASE=astro` já está no ConfigMap. Firebase e outras
   integrações precisam das suas configurações para funcionar. Faça upload do
   arquivo pelo menu do CloudShell, não pelo GitHub e não pelo chat. O JSON do
   Firebase deve ser convertido para base64 em uma única linha. Base64 não é
   criptografia; trate esse valor como segredo.

```bash
kubectl -n astro-ai create secret generic astro-ai-api-secrets \
  --from-env-file=secrets.env --dry-run=client -o yaml | kubectl apply -f -
```

Remova apenas o arquivo temporário enviado ao CloudShell após verificar o Secret.
Não apague a cópia segura das credenciais. Secrets Kubernetes não são um cofre:
limite o acesso IAM/RBAC ao cluster. Nenhum segredo é gerenciado pelo Argo CD.

5. SÓ DEPOIS dos dois Secrets, aplique o bootstrap do Argo CD a partir da `main`
   aprovada. Não execute o overlay AWS de produção, que exige ECR/ALB/ACM/domínio.

```bash
kubectl apply -f https://raw.githubusercontent.com/Astro-Inter/astro-gitops/main/argocd/academy.yaml
kubectl -n argocd get application astro-ai-api-academy
kubectl -n astro-ai get pods
kubectl -n astro-ai rollout status deployment/astro-ai-api --timeout=180s
```

O repositório é público; o Argo CD não precisa de credencial Git para lê-lo.
Verifique `Synced` e `Healthy`, e a imagem efetivamente usada:

```bash
kubectl -n astro-ai get deployment astro-ai-api -o jsonpath='{.spec.template.spec.containers[*].image}'
```

## Limites e acesso

O overlay Academy mantém API (8000) e agente A2A (8090) no mesmo Pod, com
**uma réplica**, Service **ClusterIP**, sem Ingress/Load Balancer, certificado
ou banco no EKS. Requests totais: 350m CPU e 768Mi RAM; limites totais:
1,5 CPU e 1,5Gi RAM. Não representam o consumo real: monitore o nó e os pods
antes de adicionar a segunda API. Atualizações podem interromper a API:
`maxSurge=0`, `maxUnavailable=1`, PDB `minAvailable=0` para o laboratório.
O overlay de produção no repositório de código da API permanece intacto.

Para testar `/health` e `/docs`, use um terminal LOCAL com AWS CLI/kubectl e
as credenciais temporárias do Academy (nunca as publique) e mantenha:

```bash
kubectl -n astro-ai port-forward svc/astro-ai-api 8000:80
```

Abra `http://localhost:8000/health` no mesmo computador. Um port-forward no
CloudShell NÃO é o localhost do seu computador. Para testar dentro do CloudShell,
rode port-forward em uma aba e `curl http://localhost:8000/health` em outra aba
da mesma sessão. Ainda não há URL pública para mobile/frontend; isso exige uma
etapa separada de exposição HTTPS, revisão de segurança e orçamento.
Para o painel Argo CD, o port-forward local equivalente é:

```bash
kubectl -n argocd port-forward svc/argocd-server 8080:443
```

## Diagnóstico e rollback

```bash
kubectl -n astro-ai get events --sort-by=.lastTimestamp
kubectl -n astro-ai describe deployment astro-ai-api
kubectl -n astro-ai logs deployment/astro-ai-api -c api --tail=100
kubectl -n astro-ai logs deployment/astro-ai-api -c public-research-a2a --tail=100
```

Logs podem conter dados pessoais: revise antes de compartilhar.
`ImagePullBackOff`: revisar PAT, acesso ao pacote e Secret `ghcr-read`.
`CreateContainerConfigError`: conferir os Secrets e chaves obrigatórias.
`Pending`/`OOMKilled`: conferir recursos e capacidade do único nó.
`/health` não comprova todas as integrações; testar autenticação/chat separadamente.

Para rollback duradouro, reverta o commit de código na `main`: testes, build
e GitOps publicarão uma nova imagem do código revertido. Alterações manuais no
Deployment são desfeitas por `selfHeal`. Para rollback emergencial, pause primeiro
o auto-sync e a publicação, então altere a tag no GitOps para uma imagem existente.

EKS, EC2, disco, IPv4 e tráfego continuam consumindo o orçamento do laboratório.
Fechar CloudShell não encerra esses recursos. Planeje a limpeza com cuidado;
o workflow não cria nem apaga infraestrutura AWS.
