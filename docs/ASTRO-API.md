# Ativação da API Java — SCRUM-393

## Ordem segura

1. Aprovar/merge da PR inicial do GitOps, que contém as duas APIs.
2. Configurar ASTRO_GITOPS_TOKEN nos Secrets Actions do repo astro-api:
   token fine-grained limitado ao NOVO astro-gitops, Contents e Pull requests
   Read and write, expiração curta. Não enviar token ao chat.
3. Aprovar/merge da PR de CD do astro-api. Aguardar Maven verify e build Docker,
   publicação GHCR e PR de tag neste GitOps. Aprovar/merge dessa PR de tag.
   Não sincronizar pending-first-release: é apenas marcador de imagem pendente.
4. Conferir kubectl config current-context (cluster CD-Astro, us-east-1).

```bash
aws eks update-kubeconfig --region us-east-1 --name CD-Astro
kubectl get nodes
kubectl create namespace astro-api --dry-run=client -o yaml | kubectl apply -f -
```

5. Criar ghcr-read NO NAMESPACE astro-api. Não copiar os valores via chat.
   PAT classic curto com somente read:packages, acesso ao pacote astro-api
   e SSO aprovado se exigido. Usar Bash CloudShell:

```bash
read -rp 'Usuário GitHub: ' GHCR_USER
read -rsp 'Token GHCR somente leitura: ' GHCR_READ_TOKEN
printf '\n'
kubectl -n astro-api create secret docker-registry ghcr-read \
  --docker-server=ghcr.io --docker-username="$GHCR_USER" \
  --docker-password="$GHCR_READ_TOKEN" --dry-run=client -o yaml | kubectl apply -f -
unset GHCR_READ_TOKEN GHCR_USER
```

6. Preparar secrets.env local seguindo apps/astro-api/secrets.env.example.
   PostgreSQL deve conter o schema/tabelas/funções que o backend já utiliza;
   o deploy não cria ou migra o banco (DDL auto none).
   Redis/Firebase também são externos. Firebase JSON em base64 numa linha:
   base64 NÃO é criptografia. Usar valores reais sem aspas externas/export.
   Se o provedor exigir TLS, configurar os parâmetros oficiais adequados
   (ex.: SPRING_DATA_REDIS_SSL_ENABLED=true; JDBC SSL pelo provedor); nunca
   desabilitar validação de certificado para contornar falhas.
   Fazer upload seguro do arquivo pelo CloudShell, não pelo Git ou pelo chat.

```bash
kubectl -n astro-api create secret generic astro-api-secrets \
  --from-env-file=secrets.env --dry-run=client -o yaml | kubectl apply -f -
```

Após conferir o Secret, remover só a cópia temporária no CloudShell.
Renovar tokens quando expiram. Nenhum Secret é versionado.

7. Depois da imagem aprovada e dos dois Secrets, cadastrar o projeto e a API:

```bash
kubectl apply -f https://raw.githubusercontent.com/Astro-Inter/astro-gitops/main/argocd/academy.yaml
kubectl apply -f https://raw.githubusercontent.com/Astro-Inter/astro-gitops/main/argocd/astro-api.yaml
kubectl -n argocd get application astro-api-academy
```

academy.yaml também cadastra a API de IA com auto-sync: criar primeiro seus
Secrets conforme ACADEMY.md, ou aplicar somente o documento AppProject dele.
Não aplicar cegamente antes das credenciais de ambas as APIs estarem prontas.

8. Sincronizar a Application astro-api-academy pelo Argo CD quando tudo estiver pronto.
   Ela inicia manual justamente para impedir deploy antes da primeira imagem.
   Para atualizações automáticas, abrir PR acrescentando à syncPolicy:

```yaml
automated:
  prune: true
  selfHeal: true
```

   Aprovar/merge e reaplicar argocd/astro-api.yaml. O bootstrap não é gerenciado
   por uma Application raiz; alterações nele exigem reaplicação.

```bash
kubectl -n astro-api rollout status deployment/astro-api --timeout=300s
kubectl -n astro-api get pods
kubectl -n astro-api get events --sort-by=.lastTimestamp
```

## Limites e verificação real

Uma réplica, 250m/512Mi solicitados e 1 CPU/1Gi limitados; heap JVM limitado
a 60% da memória do contêiner. Com IA+A2A, requests somam 600m/1280Mi,
além do Kubernetes e Argo CD. O t3.medium tem capacidade limitada: verificar
memória/OOM/Pending antes de ativar as duas APIs. Não há garantia de capacidade
sem medir o consumo real. Não alteramos o tamanho do nó ou orçamento AWS.

As probes TCP verificam apenas a porta 8080, pois não existe endpoint de saúde
público no código atual; não comprovam banco, Redis ou Firebase. Testar endpoints
de autenticação com conta de teste antes de considerar o deploy aprovado.
O teste de contexto completo da API está desabilitado no projeto por depender
das integrações; Maven/Docker verdes não substituem esse teste real.

Service ClusterIP, sem URL pública, Ingress ou Load Balancer.
Port-forward em terminal LOCAL:

```bash
kubectl -n astro-api port-forward svc/astro-api 8081:80
```

CloudShell localhost não é o computador do usuário. Não publicar API sem
HTTPS, revisão de acesso e orçamento. Uma réplica implica interrupção durante
atualizações (maxSurge 0/maxUnavailable 1).
Rollback: nova PR revertendo a tag para imagem publicada conhecida.
PRs antigas pendentes não são fechadas automaticamente; revisar SHA e não
aprovar versões obsoletas após uma mais recente.
