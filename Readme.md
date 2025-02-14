# AWS Port Manager

Script para gestionar excepciones de puertos en AWS Lambda.

## Uso en CloudShell

1. Clonar el repositorio:
```bash
git clone https://github.com/TU_USUARIO/aws-port-manager.git
cd aws-port-manager
```

2. Ejecutar el script:
```bash
python3 manage_exceptions.py --port NUMERO_PUERTO --description "DESCRIPCION"
```

Ejemplo:
```bash
python3 manage_exceptions.py --port 8096 --description "Puerto para Plex Media Server"
```

## Opciones

- `--port`: Número de puerto a excluir (requerido)
- `--description`: Descripción de la excepción (requerido)
- `--force`: No pedir confirmación (opcional)
