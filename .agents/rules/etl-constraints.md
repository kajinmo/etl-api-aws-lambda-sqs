---
trigger: always_on
---

# Technical Constraints & Standards

## 1. AWS & Gestão de Custos
- **Strict Free Tier:** Todas as soluções devem se manter dentro do AWS Free Tier. Se qualquer serviço ou configuração sugerida tiver risco de gerar cobrança, você deve emitir um AVISO EXPLÍCITO.
- **Segurança (IAM):** Aplique rigorosamente o Princípio do Menor Privilégio (Least Privilege). Nunca use wildcards (`*`) em permissões de S3 ou SSM. Forneça sempre o JSON exato da role/policy necessária.
- **Gestão de Segredos:** É terminantemente proibido o uso de credenciais hardcoded no código. O código Python deve obrigatoriamente usar `boto3` para buscar o Bearer Token no SSM Parameter Store.

## 2. Padrões Python
- **Tipagem e Validação:** O script de extração deve usar a biblioteca `pydantic` para estruturar e validar o payload JSON recebido da API.
- **Tratamento de Erros:** Exija blocos `try/except` robustos para lidar com falhas de requisição HTTP (status 401, 429, 500) e exceções nas chamadas do `boto3` (ex: ClientError).
- **Observabilidade:** O código deve usar o módulo nativo `logging`. É proibido o uso da função `print()`.

## 3. Padrões de Data Lake
- **Particionamento S3:** O destino no S3 deve seguir o padrão de particionamento estilo Hive usando a data de processamento (ex: `s3://meu-bucket-bronze/github_events/year=YYYY/month=MM/day=DD/`).
- **Formato:** Sendo a camada Bronze, os dados devem ser salvos em seu formato bruto (Raw JSON), sem agregações ou filtros que descartem informações originais da API.