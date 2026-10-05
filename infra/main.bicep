// Enterprise Azure API Management (APIM) Deployment with Dynamic LLM Policy
@description('The name of the Azure API Management service instance')
param apimServiceName string

@description('The name of the Azure OpenAI service account')
param azureOpenAIServiceName string

@description('The deployment environment')
@allowed([
  'dev'
  'qa'
  'prod'
])
param environment string = 'prod'

resource apimService 'Microsoft.ApiManagement/service@2023-05-01-preview' existing = {
  name: apimServiceName
}

resource openAiApi 'Microsoft.ApiManagement/service/apis@2023-05-01-preview' = {
  parent: apimService
  name: 'azure-openai-dynamic-gateway'
  properties: {
    displayName: 'Enterprise Azure OpenAI Gateway'
    description: 'Dynamic 3-Tier Model Router with Automated ERP/SAP WBS Billing'
    path: 'openai'
    protocols: [
      'https'
    ]
    subscriptionRequired: true
    format: 'openapi+json'
    value: loadTextContent('./openapi-spec.json')
  }
}

resource apiPolicy 'Microsoft.ApiManagement/service/apis/policies@2023-05-01-preview' = {
  parent: openAiApi
  name: 'policy'
  properties: {
    value: replace(loadTextContent('../policies/azure-apim-policy-enhanced.xml'), '{{azure-openai-resource-name}}', azureOpenAIServiceName)
    format: 'rawxml'
  }
}

output apiGatewayEndpoint string = '${apimService.properties.gatewayUrl}/openai'
