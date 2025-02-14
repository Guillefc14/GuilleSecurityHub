import boto3
import json
import argparse

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
            # Obtener el nombre del tema desde el ARN
            topic_name = topic_arn.split(':')[-1]
            print(f"Nombre: {topic_name}")
            print("-" * 50)
        
        return topics
    except Exception as e:
        print(f"Error al obtener temas SNS: {str(e)}")
        return None

def get_current_excluded_ports(lambda_arn):
    """Obtiene los puertos excluidos actuales"""
    try:
        response = lambda_client.get_function_configuration(FunctionName=lambda_arn)
        env_vars = response.get('Environment', {}).get('Variables', {})
        excluded_ports = env_vars.get('EXCLUDED_PORTS', '{80, 443}')
        return eval(excluded_ports)
    except Exception as e:
        print(f"Error al obtener puertos excluidos: {str(e)}")
        return {80, 443}  # Valores por defecto

def update_excluded_ports(lambda_arn, new_port, description, sns_arn):
    try:
        # Obtener puertos actuales
        current_ports = get_current_excluded_ports(lambda_arn)
        current_ports.add(new_port)
        
        # Actualizar la configuración de Lambda
        response = lambda_client.update_function_configuration(
            FunctionName=lambda_arn,
            Environment={
                'Variables': {
                    'EXCLUDED_PORTS': str(current_ports)
                }
            }
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

    # Mostrar puertos actuales
    current_ports = get_current_excluded_ports(lambda_arn)
    print(f"\nPuertos actualmente excluidos: {current_ports}")

    if port in current_ports:
        print(f"\nEl puerto {port} ya está en la lista de excepciones")
        return

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
        print(f"✅ Nuevos puertos excluidos: {get_current_excluded_ports(lambda_arn)}")
    else:
        print("\n❌ Error al añadir el puerto")

if __name__ == "__main__":
    main()
