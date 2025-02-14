import boto3
import json
import argparse
import zipfile
import tempfile
import os
import urllib.request
import io

# Nombre de la función Lambda
LAMBDA_FUNCTION_NAME = "Cierra-Puertos"

# Inicializar clientes
lambda_client = boto3.client('lambda')
sns_client = boto3.client('sns')

def get_sns_topics():
    """Obtiene y muestra todos los temas SNS disponibles"""
    try:
        response = sns_client.list_topics()
        topics = response['Topics']
        
        print("\nTemas SNS disponibles:")
        print("-" * 50)
        for topic in topics:
            topic_arn = topic['TopicArn']
            print(f"ARN: {topic_arn}")
            # Obtener el nombre del tema desde el ARN
            topic_name = topic_arn.split(':')[-1]
            print(f"Nombre: {topic_name}")
            print("-" * 50)
        
        return topics
    except Exception as e:
        print(f"Error al obtener temas SNS: {str(e)}")
        return None

def get_lambda_code():
    """Obtiene el código actual de la función Lambda"""
    try:
        response = lambda_client.get_function(FunctionName=LAMBDA_FUNCTION_NAME)
        code_location = response['Code']['Location']
        
        # Descargar el zip
        code_zip = urllib.request.urlopen(code_location).read()
        
        # Extraer el contenido
        with zipfile.ZipFile(io.BytesIO(code_zip)) as z:
            lambda_code = z.read('lambda_function.py').decode('utf-8')
            
        return lambda_code
    except Exception as e:
        print(f"Error al obtener el código Lambda: {str(e)}")
        return None

def update_excluded_ports(new_port, description, sns_arn):
    try:
        # Obtener el código actual
        current_code = get_lambda_code()
        if not current_code:
            return False
            
        # Encontrar la línea que define EXCLUDED_PORTS
        lines = current_code.split('\n')
        for i, line in enumerate(lines):
            if 'EXCLUDED_PORTS = {' in line:
                # Extraer los puertos actuales
                ports_str = line.split('{')[1].split('}')[0]
                current_ports = {int(p.strip()) for p in ports_str.split(',') if p.strip()}
                # Añadir el nuevo puerto
                current_ports.add(new_port)
                # Actualizar la línea
                lines[i] = f"EXCLUDED_PORTS = {{{', '.join(map(str, current_ports))}}}"
                break
        
        # Reconstruir el código
        updated_code = '\n'.join(lines)
        
        # Crear archivo zip temporal
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, 'lambda_function.zip')
            with zipfile.ZipFile(zip_path, 'w') as z:
                z.writestr('lambda_function.py', updated_code)
            
            # Actualizar el código de la función
            with open(zip_path, 'rb') as f:
                lambda_client.update_function_code(
                    FunctionName=LAMBDA_FUNCTION_NAME,
                    ZipFile=f.read()
                )
        
        # Enviar notificación SNS
        message = {
            "accion": "Puerto añadido a excepciones",
            "puerto": new_port,
            "descripcion": description,
            "puertos_excluidos_actuales": list(current_ports)
        }
        
        sns_client.publish(
            TopicArn=sns_arn,
            Subject=f"Nuevo puerto ({new_port}) añadido a excepciones",
            Message=json.dumps(message, indent=2)
        )
        
        return True
    except Exception as e:
        print(f"Error al actualizar puertos excluidos: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Añadir puerto a excepciones')
    parser.add_argument('--port', type=int, help='Puerto a excluir')
    parser.add_argument('--description', type=str, help='Descripción de la excepción')
    parser.add_argument('--sns-arn', type=str, help='ARN del tema SNS')
    parser.add_argument('--force', action='store_true', help='No pedir confirmación')
    
    args = parser.parse_args()
    
    # Mostrar temas SNS disponibles
    sns_topics = get_sns_topics()
    if not sns_topics:
        return

    # Solicitar puerto si no se proporcionó
    port = args.port
    while not port or not (1 <= port <= 65535):
        try:
            port = int(input("\nIntroduce el número de puerto a excluir: "))
            if not (1 <= port <= 65535):
                print("Error: El puerto debe estar entre 1 y 65535")
                port = None
        except ValueError:
            print("Error: Introduce un número válido")
            port = None

    # Solicitar descripción si no se proporcionó
    description = args.description
    while not description:
        description = input("\nIntroduce una descripción para esta excepción: ").strip()
        if not description:
            print("Error: La descripción no puede estar vacía")

    # Solicitar ARN del SNS si no se proporcionó
    sns_arn = args.sns_arn
    while not sns_arn:
        sns_arn = input("\nIntroduce el ARN del tema SNS: ").strip()
        if not sns_arn.startswith('arn:aws:sns:'):
            print("Error: El ARN debe comenzar con 'arn:aws:sns:'")
            sns_arn = None

    print("\nResumen:")
    print(f"Puerto a excluir: {port}")
    print(f"Descripción: {description}")
    print(f"ARN del SNS: {sns_arn}")
    
    if not args.force:
        confirm = input("\n¿Confirmar la acción? (s/n): ").lower()
        if confirm != 's':
            print("\nOperación cancelada")
            return
    
    if update_excluded_ports(port, description, sns_arn):
        print("\n✅ Puerto añadido exitosamente a las excepciones")
        print("✅ Notificación SNS enviada")
    else:
        print("\n❌ Error al añadir el puerto")

if __name__ == "__main__":
    main()
