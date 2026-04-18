Create a comprehensive AWS security baseline using Terraform that includes: 
1. Multi-region CloudTrail with encryption, log file validation, and CloudWatch integration 
2. GuardDuty with S3 protection and malware scanning enabled 
3. Security Hub with AWS Foundational Best Practices standard 
4. AWS WAF with OWASP Top 10 rules and rate limiting (2000 req/5min) 
5. AWS Inspector for EC2, ECR, and Lambda vulnerability scanning 
6. CloudWatch Dashboard with 8 widgets showing security metrics 
7. 4 CloudWatch Alarms: root account usage, unauthorized API calls (5+ in 5min), IAM policy changes, S3 bucket policy changes 
8. 3 IAM roles with least-privilege access: 
   - BreakGlassAdmin (requires ExternalId for emergency access) 
   - SecurityAuditor (read-only security monitoring) 
   - DeveloperTemplate (least-privilege development access) 
9. KMS encryption with auto-rotation for CloudTrail and SNS 
10. S3 state management with versioning and DynamoDB locking 
11. SNS topic for security alerts with email subscription 

Requirements: 
- Use modular Terraform structure (root + security_baseline module) 
- Include comprehensive documentation: README, QUICKSTART, SECURITY-BASELINE with SOC 2 mapping 
- Provide migration script for S3 backend 
- Include .gitignore for sensitive files 
- Add terraform.tfvars.example template 
- Create demo scripts for 5-minute and 10-minute presentations 
- Ensure all resources are tagged with Project, Environment, ManagedBy 
- Configure proper IAM policies and trust relationships 
- Enable versioning and encryption on all S3 buckets 
- Set up metric filters for security event detection 

Output should be production-ready, well-documented, and deployable in under 10 minutes.
