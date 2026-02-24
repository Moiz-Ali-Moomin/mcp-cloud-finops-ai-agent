# ☁️ OpsYield MCP FinOps Server

> [!WARNING]
> **Cloud Spending Alert**: This tool queries billing and cost APIs. Large queries or high-frequency polling may incur API costs or data egress charges depending on your cloud provider's pricing tier (e.g., BigQuery analysis costs for GCP).

OpsYield MCP FinOps is a Model Context Protocol (MCP) server that provides real-time financial operations (FinOps) intelligence for **AWS**, **GCP**, and **Azure**. It allows AI models (like Claude) to analyze your cloud costs, identify waste, and suggest optimizations directly within your chat interface.

---

## 🚀 Quick Start (Local Setup)

### 1. Prerequisites
- **Python 3.10+** (Recommended: 3.13)
- **pip** (Python package manager)
- **Cloud Accounts**: Active credentials for at least one provider (AWS, GCP, or Azure).

### 2. Installation
Clone the repository and install dependencies:

```bash
git clone <repository-url>
cd "MCP FinOps"
pip install -r requirements.txt
```

---

## 📂 OS-Specific Configuration

The server runs as a `stdio` MCP server. You need to configure your environment variables based on your Operating System.

### 🪟 Windows (PowerShell)
Set environment variables for your current session:
```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\your\gcp-sa.json"
$env:GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
$env:AWS_PROFILE="default"
$env:AZURE_SUBSCRIPTION_ID="your-sub-id"
```

### 🍎 macOS / 🐧 Linux (Bash/Zsh)
Add these to your `~/.bashrc` or `~/.zshrc`:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/gcp-sa.json"
export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
export AWS_PROFILE="default"
export AZURE_SUBSCRIPTION_ID="your-sub-id"
```

---

## 🔐 Cloud Authentication Setup

### 🔵 Google Cloud Platform (GCP)
1.  **Service Account**: Create a Service Account in the [GCP Console](https://console.cloud.google.com/iam-admin/serviceaccounts).
2.  **Permissions**: Assign the following roles:
    *   `BigQuery Data Viewer`
    *   `BigQuery Job User`
    *   `Compute Viewer` (for resource discovery)
3.  **JSON Key**: Generate a JSON key and save it locally. Set the path in `GOOGLE_APPLICATION_CREDENTIALS`.
4.  **Billing Export**: Ensure **Billing Export to BigQuery** is enabled in your Billing Account settings.

### 🟠 Amazon Web Services (AWS)
1.  **IAM User**: Create an IAM user or role.
2.  **Permissions**: Attach a policy with:
    *   `ce:GetCostAndUsage` (Cost Explorer)
    *   `ec2:DescribeInstances`
    *   `s3:ListAllMyBuckets`
3.  **CLI Config**: Run `aws configure` to set up your local credentials profile.

### ⚪ Microsoft Azure
1.  **Service Principal**: Create an App Registration (Service Principal) in Azure AD.
2.  **Secret**: Create a Client Secret.
3.  **Permissions**: Assign the `Cost Management Reader` role at the Subscription level.
4.  **Env Vars**:
    *   `AZURE_CLIENT_ID`: Your App Registration ID.
    *   `AZURE_CLIENT_SECRET`: Your Client Secret.
    *   `AZURE_TENANT_ID`: Your Directory ID.
    *   `AZURE_SUBSCRIPTION_ID`: Your Subscription ID.

---

## 🤖 Integration with Claude Desktop

To use this with Claude Desktop, edit your `claude_desktop_config.json`:

**Path**: `%APPDATA%\Claude\claude_desktop_config.json` (Windows)

OR

**Path**: `%AppData%\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude_desktop_config.json` (Windows)

`The Claude desktop_config Path can be different and the folder name (Claude_pzs8sxrjxfjjc) can also be Different Search for Claude Folder in Search Bar`

```json
{
  "mcpServers": {
    "opsyield-finops": {
      "command": "python",
      "args": ["C:\\absolute\\path\\to\\mcp_server.py"],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "C:\\path\\to\\gcp-sa.json",
        "GOOGLE_CLOUD_PROJECT": "your-project-id",
        "AWS_REGION": "us-east-1",
        "AZURE_SUBSCRIPTION_ID": "..."
      }
    }
  }
}
```

---

## 🛠️ Usage

Once connected, you can ask Claude:
- *"Show me my AWS costs for the last 30 days."*
- *"List any idle resources in my GCP project."*
- *"What is the projected Azure spend for this month?"*

---

## ❓ Troubleshooting

- **GCP 404 (Table Not Found)**: Verify that your Billing Export dataset name matches the expected pattern in `mcp_server.py`.
- **AWS Permission Denied**: Ensure "Cost Explorer" is enabled in the AWS Billing console (it's often disabled by default).
- **Timeout Erros**: If queries take >60s, check your network or try reducing the `days` parameter.
