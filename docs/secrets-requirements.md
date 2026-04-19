# secrets

I need to be able to add secrets to skills and mcp configurations in a secure fashion.  
I use an Azure Key vault to store my secrets and would like to be able to reference those secrets.
ollm can assume that the user has already authenticated with Azure and has access to the referenced key vault.
The name of the key vault will be stored in config.json as "keyvault". ollm will construct the url from that.
to reference a secret in the keyvault in a skill or mcp configuration using handlebars syntax.  For example if I have a google search API key in my vault as a secret called GoogleSearchKey, it would be referenced as:
{GoogleSearchKey}.  Encountering this reference ollm will fetch the secret from the vault and use the secrets value in its place.
ollm should test access to the key vault on start up and display a warning if it is unable to access the vault and continue.
when ollm encounters a secret reference and is either unable to access the secret or the secret does not exist it should display a warning to the user but continue execution.

## Clarifications
secret scope: secret substitution should occur in mcp.json, skills and skills resource files.
Azure auth: assume Azure CLI (az login) because that is how my other tools work.
secret cashing: cache secret values in memory
cache invalidation: since ollm is not a long running process there is no need to worry about values changing. ollm runs the prompt, processes the output and exits.  if something runs it again the secrets will be reloaded at that time making this a non-concern.
nested secrets: just simple key names
default values: default values would be cool.  separate the secret reference from the default value using a colon. Like so: {GoogleSearchKey:default_value}
secret validation: yes, validate that the braces are closed
startup behavior: if the vault cannot be accessed, continue w/ a warning and fail fast on secret references
partial failures: show a warning when a secret cannot be accessed
template processing: just use a simple regex approach
When to process: at configuration load time.
configuration scheam: use transparent string processing
fail fast secret references: when the vault can't be accessed we shouldnt bother trying to fetch the secret when we encounter a reference.  But if a secret provides a default value - use it.
my vaults name: kvGPSecrets