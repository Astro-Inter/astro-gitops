# NodePorts para ALB interno no Academy

SCRUM-393. Este guia prepara os destinos de um ALB configurado fora do Argo CD.
Os patches afetam somente os overlays Academy; os Services base permanecem ClusterIP.
Nao altera imagens, Secrets, replicas nem a politica de sincronizacao do Argo CD.

| Namespace | Service | Porta interna | NodePort TCP | Health check HTTP sugerido |
| --- | --- | --- | --- | --- |
| astro-ai | astro-ai-api | 80 | 30080 | /health (200) |
| astro-api | astro-api | 80 | 30081 | /v3/api-docs (200) |

A porta 8090 do agente A2A nao e exposta por estes patches.
O health check da Java acima verifica a resposta HTTP da documentacao, nao a saude
completa do banco, Redis ou Firebase. Teste as operacoes autenticadas separadamente.

## Antes do merge

1. Confira se 30080 e 30081 nao estao ocupadas por outros Services no cluster:

   ```bash
   kubectl get services -A -o custom-columns='NAMESPACE:.metadata.namespace,NAME:.metadata.name,NODEPORTS:.spec.ports[*].nodePort'
   ```

2. Identifique a zona e a instancia do no atual (nao reutilize IDs de capturas antigas):

   ```bash
   kubectl get nodes -L topology.kubernetes.io/zone
   kubectl get nodes -o custom-columns='NAME:.metadata.name,PROVIDER:.spec.providerID'
   ```

   O ALB precisa habilitar a zona do no registrado como destino. Se o no estiver em
   us-east-1d e o formulario tiver somente us-east-1a/b, inclua us-east-1d tambem.
   As sub-redes do ALB e do VPC Link nao precisam ser identicas.

3. Confira os grupos de seguranca associados a instancia. Antes da sincronizacao,
   remova eventuais regras amplas que permitam acesso publico aos NodePorts.
   Nao libere 30080/30081 nem todo o intervalo 30000-32767 para 0.0.0.0/0 ou ::/0.
   NodePort pode aceitar trafego em todos os nos; revise todos os grupos aplicaveis.

## Fluxo de seguranca

- VPC Link: grupo separado astro-vpc-link-sg; sem entrada. Quando o ALB estiver
  definido, restrinja a saida as portas dos listeners e ao grupo astro-alb-sg.
- ALB interno: astro-alb-sg aceita nas portas dos listeners apenas a origem
  astro-vpc-link-sg. Sua saida deve permitir TCP 30080 e 30081 ao grupo dos nos.
- Nos: entrada TCP 30080 e TCP 30081 com origem exclusivamente astro-alb-sg.
  Preserve as regras internas necessarias ao EKS; nao remova regras sem avaliar
  seu uso. Revise tambem acessos por CIDR que possam contornar essa restricao.

NodePort sozinho nao implementa firewall nem HTTPS. A protecao depende das regras
AWS acima. HTTPS publico sera configurado no API Gateway; trafego HTTP entre
VPC Link, ALB e nos permanece privado, mas nao e criptografado por estes manifestos.
O painel Argo CD continua privado.

## Aplicacao e destinos

Depois da revisao de seguranca, aprove e faca merge da PR. A IA tem sincronizacao
automatica; a Java permanece manual e precisa de Sync no Argo CD. Nao aplique
os patches por kubectl fora do fluxo GitOps.

Confirme apos sincronizar:

```bash
kubectl -n astro-ai get service astro-ai-api
kubectl -n astro-api get service astro-api
```

Prepare dois target groups do tipo Instances, na mesma VPC, protocolo HTTP:
um em 30080 para IA, outro em 30081 para Java. Registre a instancia atual do EKS
nas portas correspondentes. Use os health checks da tabela, na porta de trafego.
Nao registre IP de Pod manualmente: ele pode mudar a cada atualizacao.
Configure o encaminhamento de cada API separadamente; nao distribua chamadas
aleatoriamente entre os dois grupos. Os paths do backend devem ser preservados.

O ALB, VPC Link, listeners e target groups nao sao provisionados por esta PR.
ALB e API Gateway possuem cobrancas separadas. Confira o orcamento antes de criar.
A abordagem manual exige revisar os destinos quando um no e substituido; considere
integracao com o Auto Scaling Group, verificando permissoes e comportamento do
grupo gerenciado, em uma etapa separada. Academy pode interromper os nos ao
encerrar a sessao; nao e disponibilidade de producao.

## Reversao

Reverta esta PR por outra PR aprovada para retornar os overlays a ClusterIP,
e sincronize as Applications. Remova as regras AWS especificas quando deixarem
de ser necessarias. O revert no Git nao exclui ALB/API Gateway nem encerra suas
cobrancas: a limpeza desses recursos e uma operacao separada.
