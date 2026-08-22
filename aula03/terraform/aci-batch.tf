# ---------------------------------------------------------------------------
# Exercício 2.3 — Endurecer e dimensionar o ACI
# Variante BATCH do ACI do lab, para comparação lado a lado:
#   (a) restart_policy = "OnFailure"  — job que termina e nao deve reiniciar
#   (b) right-sizing    1 vCPU / 2 GB — dobro do lab (0.5 / 1.0)
#   (c) secure_environment_variables  — valor nao aparece no 'az container show'
# ---------------------------------------------------------------------------

resource "random_password" "qc_api_token" {
  length  = 32
  special = false
}

resource "azurerm_container_group" "aci_batch" {
  count = var.aci_enabled ? 1 : 0

  name                = "aci-qc-batch-${random_string.sufixo.result}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  os_type             = "Linux"
  ip_address_type     = "None" # job batch nao expoe porta
  restart_policy      = "OnFailure"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.aci_id.id]
  }

  image_registry_credential {
    server   = azurerm_container_registry.acr.login_server
    username = azurerm_container_registry.acr.admin_username
    password = azurerm_container_registry.acr.admin_password
  }

  container {
    name   = "recalculo-recomendacoes"
    image  = "${azurerm_container_registry.acr.login_server}/produtos-api:v1"
    cpu    = "1"
    memory = "2"

    # Sobrescreve o entrypoint da imagem: simula o job noturno que roda e termina.
    commands = [
      "python", "-c",
      "import os,time; print('[batch] recalculo iniciado'); time.sleep(20); print('[batch] token presente:', bool(os.environ.get('QC_API_TOKEN'))); print('[batch] concluido')"
    ]

    # (c) NAO sensivel — aparece em texto plano no portal/CLI
    environment_variables = {
      QC_MODO                  = "batch"
      STORAGE_ACCOUNT_CATALOGO = azurerm_storage_account.catalogo.name
    }

    # (c) sensivel — o CLI retorna value: null
    secure_environment_variables = {
      QC_API_TOKEN = random_password.qc_api_token.result
    }
  }

  tags = local.tags
}

output "aci_batch_name" {
  description = "Nome do ACI batch (2.3) quando habilitado"
  value       = var.aci_enabled ? azurerm_container_group.aci_batch[0].name : "habilite com -var aci_enabled=true"
}
