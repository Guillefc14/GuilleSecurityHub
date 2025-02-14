import boto3
import json
import argparse
import base64

# Inicializar clientes
lambda_client = boto3.client('lambda')
sns_client = boto3.client('sns')

def get_lambda_functions():
    """Obtiene y muestra todas las funciones Lambda disponibles"""
    try:
        response = lambda_client.list_functions()
        functions = response['Functions']
        
        print("\nFunciones Lambda disponibles:")
        print("-" * 50)
        for function in functions:
            function_arn = function['FunctionArn']
            function_name = function['FunctionName']
            print(f"Nombre: {function_name}")
            print(f"ARN: {function_arn}")
            print("-" * 50)
        
        return functions
    except Exception as e:
        print(f"Error al obtener funciones Lambda: {str(e)}")
        return None

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
            topic_name = topic_arn.split(':')[-1]
            print(f"Nombre: {topic_name}")
            print("-" * 50)
        
        return topics
    except Exception as e:
        print(f"Error al obtener temas SNS: {str(e)}")
        return None

def get_lambda_code(lambda_arn):
    """Obtiene el código actual de la función Lambda"""
    try:
        response = lambda_client.get_function(FunctionName=lambda_arn)
        location = response['Code']['Location']
        
        # Obtener el código fuente
        import urllib.request
        with urllib.request.urlopen(location) as f:
            code = f.read()
        
        return code
    except Exception as e:
        print(f"Error al obtener código Lambda: {str(e)}")
        return None

def update_excluded_ports(lambda_arn, new_port, description, sns_arn):
    try:
        # Descargar el código actual
        code = get_lambda_code(lambda_arn)
        if not code:
            return False
        
        # Crear un archivo ZIP temporal con el código actualizado
        import tempfile
        import zipfile
        import os
        
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "function.zip")
            
            # Extraer el código actual
            with open(os.path.join(tmpdir, "lambda_function.zip"), "wb") as f:
                f.write(code)
            
            # Extraer el archivo ZIP
            with zipfile.ZipFile(os.path.join(tmpdir, "lambda_function.zip"), 'r') as zip_ref:
                zip_ref.extractall(tmpdir)
            
            # Leer el código Python
            with open(os.path.join(tmpdir, "lambda_function.py"), 'r') as f:
                lambda_code = f.read()
            
            # Modificar la línea de EXCLUDED_PORTS
            lines = lambda_code.split('\n')
            for i, line in enumerate(lines):
                if 'EXCLUDED_PORTS = {' in line:
                    current_ports = eval(line.split('=')[1].strip())
                    current_ports.add(new_port)
                    lines[i] = f"EXCLUDED_PORTS = {current_ports}"
                    break
            
            # Guardar el código modificado
            with open(os.path.join(tmpdir, "lambda_function.py"), 'w') as f:
                f.write('\n'.join(lines))
            
            # Crear nuevo ZIP
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                zipf.write(os.path.join(tmpdir, "lambda_function.py"), "lambda_function.py")
            
            # Actualizar la función Lambda
            with open(zip_path, 'rb') as f:
                lambda_client.update_function_code(
                    FunctionName=lambda_arn,
                    ZipFile=f.read()
                )
        
        # Enviar notificación SNS
        message = {
            "accion": "Puerto añadido a excepciones",
            "funcion_lambda": lambda_arn,
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
    parser.add_argument('--lambda-arn', type=str, help='ARN de la función Lambda')
    parser.add_argument('--sns-arn', type=str, help='ARN del tema SNS')
    parser.add_argument('--force', action='store_true', help='No pedir confirmación')
    
    args = parser.parse_args()

    # Mostrar funciones Lambda disponibles
    lambda_functions = get_lambda_functions()
    if not lambda_functions:
        return
    
    # Mostrar temas SNS disponibles
    sns_topics = get_sns_topics()
    if not sns_topics:
        return

    # Solicitar ARN de Lambda si no se proporcionó
    lambda_arn = args.lambda_arn
    while not lambda_arn:
        lambda_arn = input("\nIntroduce el ARN de la función Lambda: ").strip()
        if not lambda_arn.startswith('arn:aws:lambda:'):
            print("Error: El ARN debe comenzar con 'arn:aws:lambda:'")
            lambda_arn = None

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
    print(f"Función Lambda: {lambda_arn}")
    print(f"Puerto a excluir: {port}")
    print(f"Descripción: {description}")
    print(f"ARN del SNS: {sns_arn}")
    
    if not args.force:
        confirm = input("\n¿Confirmar la acción? (s/n): ").lower()
        if confirm != 's':
            print("\nOperación cancelada")
            return
    
    if update_excluded_ports(lambda_arn, port, description, sns_arn):
        print("\n✅ Puerto añadido exitosamente a las excepciones")
        print("✅ Notificación SNS enviada")
    else:
        print("\n❌ Error al añadir el puerto")

if __name__ == "__main__":
    main()
