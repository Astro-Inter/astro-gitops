# Astro GitOps

Configuração central das aplicações Astro que desejamos executar no Kubernetes
do AWS Academy. Tarefa inicial: SCRUM-393.

Fluxo: código aprovado na main da API → testes → imagem GHCR →
branch com nova tag → PR neste repositório → aprovação e merge na main →
Argo CD → EKS CD-Astro.

## Aplicações cadastradas

| Aplicação | Código | Configuração | Argo CD |
| --- | --- | --- | --- |
| API de IA (API + agente A2A no mesmo Pod) | [astro-ai-api](https://github.com/Astro-Inter/astro-ai-api) | apps/astro-ai-api/overlays/academy | astro-ai-api-academy |
| API Java | [astro-api](https://github.com/Astro-Inter/astro-api) | apps/astro-api/overlays/academy | astro-api-academy |

As duas APIs estão cadastradas, mas a Java aguarda a primeira imagem publicada
e aprovada, Secrets e ativação conforme docs/ASTRO-API.md.
Nenhuma aplicação sobe apenas por existir na
organização; cada uma precisa de manifestos e de uma Application do Argo CD.

## Organização

- apps/<nome>/base: Deployment, Service, ConfigMap e demais recursos da aplicação.
- apps/<nome>/overlays/academy: configuração específica do laboratório.
- argocd/academy.yaml: AppProject e Application, apontando para a main deste repo.
- docs/ACADEMY.md: ativação, tokens, Secrets e diagnóstico.

Argo CD já está instalado no cluster; o bootstrap apenas cadastra a API nele.
Não há Application gerenciando a instalação do próprio Argo CD.
Este repo não provisiona EKS, EC2 ou outros recursos AWS.

## Segurança e alterações

Repositório público: nunca commitar senhas, tokens, .env real ou YAML de Secret.
Os Secrets são criados diretamente no cluster, fora do Git.
Somente exemplos sem valores secretos podem ser versionados.

Todas as alterações entram por branches e PRs, inclusive as tags automáticas.
A main exige uma aprovação de outra pessoa, invalida aprovações após novas
alterações, exige o check validate, branch atualizada e conversas resolvidas.
As regras valem também para administradores. Force push e exclusão são proibidos.
O workflow nunca faz merge nem aprova a própria PR.
Argo CD observa somente a main; uma PR pendente não é implantada.

A main foi iniciada com um commit vazio para permitir sua proteção.
Nenhum arquivo de configuração foi enviado diretamente para ela: a configuração
inicial também depende de PR aprovada.

O token de escrita deve ter Contents e Pull requests read/write limitado a este repo, sem
administração, acesso a outros repos ou permissões AWS. Cada aplicação futura
precisa de sua integração; não reutilize tokens com acesso amplo.

Para validar localmente:

```bash
kubectl kustomize apps/astro-ai-api/overlays/academy
kubectl kustomize apps/astro-api/overlays/academy
python -m pip install 'PyYAML>=6,<7'
python -m unittest discover -s tests
```

Consulte [o guia de ativação](docs/ACADEMY.md) antes de aplicar o bootstrap.
Ter arquivos no GitHub não significa que a API já esteja no ar.
