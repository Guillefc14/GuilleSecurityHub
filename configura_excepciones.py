import boto3
import json
import tempfile
import zipfile
import os
import urllib.request

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

def get_lambda_code_and_ports(lambda_arn):
    """Obtiene el código actual y los puertos excluidos"""
    try:
        response = lambda_client.get_function(FunctionName=lambda_arn)
        location = response['Code']['Location']
        
        # Descargar el código
        with urllib.request.urlopen(location) as f:
            code = f.read()
            
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "lambda_function.zip")
            
            # Guardar el ZIP
            with open(zip_path, "wb") as f:
                f.write(code)
            
            # Extraer el ZIP
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(tmpdir)
            
            # Leer el código Python
            with open(os.path.join(tmpdir, "lambda_function.py"), 'r') as f:
                lambda_code = f.read()
            
            # Obtener puertos excluidos
            for line in lambda_code.split('\n'):
                if 'EXCLUDED_PORTS = {' in line:
                    ports = eval(line.split('=')[1].strip())
                    return lambda_code, ports
                    
        return None, set()
    except Exception as e:
        print(f"Error al obtener código Lambda: {str(e)}")
        return None, set()

def update_lambda_code(lambda_arn, ports, description, sns_arn):
    """Actualiza el código de la función Lambda"""
    try:
        # Obtener el código actual
        current_code, _ = get_lambda_code_and_ports(lambda_arn)
        if not current_code:
            return False
            
        # Modificar la línea de EXCLUDED_PORTS
        new_lines = []
        for line in current_code.split('\n'):
            if 'EXCLUDED_PORTS = {' in line:
                new_lines.append(f"EXCLUDED_PORTS = {ports}")
            else:
                new_lines.append(line)
        
        new_code = '\n'.join(new_lines)
        
        # Crear nuevo ZIP
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "function.zip")
            
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                zipf.writestr('lambda_function.py', new_code)
            
            # Actualizar la función Lambda
            with open(zip_path, 'rb') as f:
                lambda_client.update_function_code(
                    FunctionName=lambda_arn,
                    ZipFile=f.read()
                )
        
        # Enviar notificación SNS
        message = {
            "accion": "Puertos excluidos actualizados",
            "funcion_lambda": lambda_arn,
            "puertos_excluidos":list(ports),
            "descripcion": description
        }
        
        sns_client.publish(
            TopicArn=sns_arn,
            Subject=f"Puertos excluidos actualizados",
            Message=json.dumps(message, indent=2)
        )
        
        return True
    except Exception as e:
        print(f"Error al actualizar código Lambda: {str(e)}")
        return False

def main():
    print("\n=== Gestor de Puertos Excluidos ===")
    
    # Mostrar funciones Lambda disponibles
    lambda_functions = get_lambda_functions()
    if not lambda_functions:
        return

    # Mostrar temas SNS disponibles
    sns_topics = get_sns_topics()
    if not sns_topics:
        return

    # Solicitar ARN de Lambda
    lambda_arn = input("\nIntroduce el ARN de la función Lambda: ").strip()
    if not lambda_arn.startswith('arn:aws:lambda:'):
        print("Error: El ARN debe comenzar con 'arn:aws:lambda:'")
        return

    # Solicitar ARN del SNS
    sns_arn = input("\nIntroduce el ARN del tema SNS: ").strip()
    if not sns_arn.startswith('arn:aws:sns:'):
        print("Error: El ARN debe comenzar con 'arn:aws:sns:'")
        return

    while True:
        # Obtener código y puertos actuales
        _, current_ports = get_lambda_code_and_ports(lambda_arn)
        
        print("\nPuertos actualmente excluidos:")
        print("-" * 50)
        for port in sorted(current_ports):
            print(f"Puerto: {port}")
        print("-" * 50)

        print("\n=== Menú de Opciones ===")
        print("1. Añadir puerto")
        print("2. Eliminar puerto")
        print("3. Salir")
        
        option = input("\nSelecciona una opción (1-3): ").strip()

        if option == "1":
            try:
                port = int(input("\nIntroduce el número de puerto a añadir: "))
                if not (1 <= port <= 65535):
                    print("Error: El puerto debe estar entre 1 y 65535")
                    continue
                
                if port in current_ports:
                    print(f"El puerto {port} ya está en la lista de excepciones")
                    continue
                
                description = input("\nIntroduce una descripción para esta excepción: ").strip()
                if not description:
                    print("Error: La descripción no puede estar vacía")
                    continue

                current_ports.add(port)
                if update_lambda_code(lambda_arn, current_ports, description, sns_arn):
                    print("\n✅ Puerto añadido exitosamente")
                else:
                    print("\n❌ Error al añadir el puerto")
            
            except ValueError:
                print("Error: Introduce un número válido")

        elif option == "2":
            if not current_ports:
                print("\nNo hay puertos excluidos para eliminar")
                continue
            
            try:
                port = int(input("\nIntroduce el número de puerto a eliminar: "))
                if port not in current_ports:
                    print(f"El puerto {port} no está en la lista de excepciones")
                    continue
                
                current_ports.remove(port)
                if update_lambda_code(lambda_arn, current_ports, f"Eliminado puerto {port}", sns_arn):
                    print("\n✅ Puerto eliminado exitosamente")
                else:
                    print("\n❌ Error al eliminar el puerto")
            
            except ValueError:
                print("Error: Introduce un número válido")

        elif option == "3":
            print("\n¡Hasta luego!")
            break

        else:
            print("\nOpción no válida. Por favor, selecciona una opción válida (1-3)")

if __name__ == "__main__":
    main()
