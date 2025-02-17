import boto3
import json

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

def get_excluded_ports(lambda_arn):
    """Obtiene los puertos excluidos actuales"""
    try:
        response = lambda_client.get_function_configuration(FunctionName=lambda_arn)
        env_vars = response.get('Environment', {}).get('Variables', {})
        excluded_ports = env_vars.get('EXCLUDED_PORTS', '{80, 443}')
        return eval(excluded_ports)
    except Exception as e:
        print(f"Error al obtener puertos excluidos: {str(e)}")
        return set([80, 443])

def update_excluded_ports(lambda_arn, ports, description, sns_arn):
    """Actualiza los puertos excluidos"""
    try:
        # Actualizar la configuración de Lambda
        response = lambda_client.update_function_configuration(
            FunctionName=lambda_arn,
            Environment={
                'Variables': {
                    'EXCLUDED_PORTS': str(ports)
                }
            }
        )
        
        # Enviar notificación SNS
        message = {
            "accion": "Puertos excluidos actualizados",
            "funcion_lambda": lambda_arn,
            "puertos_excluidos": list(ports),
            "descripcion": description
        }
        
        sns_client.publish(
            TopicArn=sns_arn,
            Subject=f"Puertos excluidos actualizados",
            Message=json.dumps(message, indent=2)
        )
        
        return True
    except Exception as e:
        print(f"Error al actualizar puertos excluidos: {str(e)}")
        return False

def main():
    print("\n=== Gestor de Puertos Excluidos ===")
    
    # Mostrar funciones Lambda disponibles
    lambda_functions = get_lambda_functions()
    if not lambda_functions:
        return

    # Solicitar ARN de Lambda
    lambda_arn = ""
    while not lambda_arn:
        lambda_arn = input("\nIntroduce el ARN de la función Lambda: ").strip()
        if not lambda_arn.startswith('arn:aws:lambda:'):
            print("Error: El ARN debe comenzar con 'arn:aws:lambda:'")
            lambda_arn = ""

    while True:
        # Mostrar menú principal
        print("\n=== Menú Principal ===")
        print("1. Listar puertos excluidos")
        print("2. Añadir puerto")
        print("3. Eliminar puerto")
        print("4. Salir")
        
        option = input("\nSelecciona una opción (1-4): ").strip()
        
        if option == "1":
            # Listar puertos
            current_ports = get_excluded_ports(lambda_arn)
            print("\nPuertos actualmente excluidos:")
            print("-" * 50)
            for port in sorted(current_ports):
                print(f"Puerto: {port}")
            print("-" * 50)
            
        elif option == "2" or option == "3":
            # Mostrar temas SNS disponibles
            sns_topics = get_sns_topics()
            if not sns_topics:
                continue
            
            # Solicitar ARN del SNS
            sns_arn = ""
            while not sns_arn:
                sns_arn = input("\nIntroduce el ARN del tema SNS: ").strip()
                if not sns_arn.startswith('arn:aws:sns:'):
                    print("Error: El ARN debe comenzar con 'arn:aws:sns:'")
                    sns_arn = ""
            
            # Obtener puertos actuales
            current_ports = get_excluded_ports(lambda_arn)
            
            # Solicitar puerto
            port = 0
            while not (1 <= port <= 65535):
                try:
                    port = int(input("\nIntroduce el número de puerto: "))
                    if not (1 <= port <= 65535):
                        print("Error: El puerto debe estar entre 1 y 65535")
                        port = 0
                except ValueError:
                    print("Error: Introduce un número válido")
                    port = 0
            
            if option == "2":  # Añadir
                if port in current_ports:
                    print(f"\nEl puerto {port} ya está en la lista de excepciones")
                    continue
                
                description = ""
                while not description:
                    description = input("\nIntroduce una descripción para esta excepción: ").strip()
                    if not description:
                        print("Error: La descripción no puede estar vacía")
                
                current_ports.add(port)
                action_desc = "Añadir"
            else:  # Eliminar
                if port not in current_ports:
                    print(f"\nEl puerto {port} no está en la lista de excepciones")
                    continue
                
                current_ports.remove(port)
                description = f"Eliminado puerto {port}"
                action_desc = "Eliminar"
            
            print("\nResumen:")
            print(f"Acción: {action_desc} excepción")
            print(f"Función Lambda: {lambda_arn}")
            print(f"Puerto: {port}")
            if option == "2":
                print(f"Descripción: {description}")
            print(f"ARN del SNS: {sns_arn}")
            
            confirm = input("\n¿Confirmar la acción? (s/n): ").lower()
            if confirm != 's':
                print("\nOperación cancelada")
                continue
            
            if update_excluded_ports(lambda_arn, current_ports, description, sns_arn):
                print("\n✅ Puertos excluidos actualizados exitosamente")
                print("✅ Notificación SNS enviada")
                print("\nNueva lista de puertos excluidos:")
                print("-" * 50)
                for port in sorted(current_ports):
                    print(f"Puerto: {port}")
                print("-" * 50)
            else:
                print("\n❌ Error al actualizar los puertos excluidos")
            
        elif option == "4":
            print("\n¡Hasta luego!")
            break
            
        else:
            print("\nOpción no válida. Por favor, selecciona una opción válida (1-4)")

if __name__ == "__main__":
    main()
