resource "aws_instance" "backend" {
  ami                         = data.aws_ami.amazon_linux_2023.id
  instance_type               = var.instance_type
  key_name                    = var.key_name
  subnet_id                   = data.aws_subnets.default.ids[0]
  vpc_security_group_ids      = [aws_security_group.backend.id]
  associate_public_ip_address = true

  root_block_device {
    volume_size = var.volume_size_gb
    volume_type = "gp3"
    encrypted   = true
  }

  user_data = <<-USERDATA
    #!/usr/bin/env bash
    set -euo pipefail
    dnf update -y
    dnf install -y docker git tar gzip --allowerasing
    systemctl enable --now docker
    mkdir -p /usr/local/lib/docker/cli-plugins
    curl -fsSL https://github.com/docker/compose/releases/download/v2.29.7/docker-compose-linux-x86_64 \
      -o /usr/local/lib/docker/cli-plugins/docker-compose
    chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
    usermod -aG docker ec2-user || true
  USERDATA

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-backend"
  })
}
