def get_current_excluded_ports(lambda_arn):
    """Obtiene los puertos actualmente excluidos"""
    try:
        code = get_lambda_code(lambda_arn)
        if not code:
            return None

        # Crear un archivo temporal y extraer el código
        import tempfile
        import zipfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            # Extraer el código actual
            with open(os.path.join(tmpdir, "lambda_function.zip"), "wb") as f:
                f.write(code)

            # Extraer el archivo ZIP
            with zipfile.ZipFile(os.path.join(tmpdir, "lambda_function.zip"), 'r') as zip_ref:
                zip_ref.extractall(tmpdir)

            # Leer el código Python
            with open(os.path.join(tmpdir, "lambda_function.py"), 'r') as f:
                lambda_code = f.read()

            # Buscar la línea de EXCLUDED_PORTS
            for line in lambda_code.split('\n'):
                if 'EXCLUDED_PORTS = {' in line:
                    return eval(line.split('=')[1].strip())

        return set()
    except Exception as e:
        print(f"Error al obtener puertos excluidos: {str(e)}")
        return None

def remove_excluded_port(lambda_arn, port_to_remove, sns_arn):
    """Elimina un puerto de las excepciones"""
    try:
        code = get_lambda_code(lambda_arn)
        if not code:
            return False

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
                    if port_to_remove not in current_ports:
                        print(f"El puerto {port_to_remove} no está en la lista de excepciones")
                        return False
                    current_ports.remove(port_to_remove)
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
                "accion": "Puerto eliminado de excepciones",
                "funcion_lambda": lambda_arn,
                "puerto": port_to_remove,
                "puertos_excluidos_actuales": list(current_ports)
            }

            sns_client.publish(
                TopicArn=sns_arn,
                Subject=f"Puerto ({port_to_remove}) eliminado de excepciones",
                Message=json.dumps(message, indent=2)
            )

            return True
    except Exception as e:
        print(f"Error al eliminar puerto excluido: {str(e)}")
        return False

def main():
    # Mostrar funciones Lambda disponibles
    lambda_functions = get_lambda_functions()
    if not lambda_functions:
        return

    # Solicitar ARN de Lambda
    lambda_arn = input("\nIntroduce el ARN de la función Lambda: ").strip()
    if not lambda_arn.startswith('arn:aws:lambda:'):
        print("Error: El ARN debe comenzar con 'arn:aws:lambda:'")
        return

    while True:
        print("\n=== Menú de Gestión de Puertos Excluidos ===")
        print("1. Listar puertos excluidos")
        print("2. Añadir puerto")
        print("3. Eliminar puerto")
        print("4. Salir")

        option = input("\nSelecciona una opción (1-4): ")

        if option == "1":
            # Listar puertos
            current_ports = get_current_excluded_ports(lambda_arn)
            if current_ports:
                print("\nPuertos actualmente excluidos:")
                print("-" * 50)
                for port in sorted(current_ports):
                    print(f"Puerto: {port}")
                print("-" * 50)

        elif option == "2":
            # Añadir puerto (código existente)
            # Mostrar temas SNS disponibles
            sns_topics = get_sns_topics()
            if not sns_topics:
                continue

            port = 0
            while not (1 <= port <= 65535):
                try:
                    port = int(input("\nIntroduce el número de puerto a excluir: "))
                    if not (1 <= port <= 65535):
                        print("Error: El puerto debe estar entre 1 y 65535")
                        port = 0
                except ValueError:
                    print("Error: Introduce un número válido")
                    port = 0

            description = ""
            while not description:
                description = input("\nIntroduce una descripción para esta excepción: ").strip()
                if not description:
                    print("Error: La descripción no puede estar vacía")

            sns_arn = input("\nIntroduce el ARN del tema SNS: ").strip()
            if not sns_arn.startswith('arn:aws:sns:'):
                print("Error: El ARN debe comenzar con 'arn:aws:sns:'")
                continue

            if update_excluded_ports(lambda_arn, port, description, sns_arn):
                print("\n✅ Puerto añadido exitosamente a las excepciones")
                print("✅ Notificación SNS enviada")
            else:
                print("\n❌ Error al añadir el puerto")

        elif option == "3":
            # Eliminar puerto
            sns_topics = get_sns_topics()
            if not sns_topics:
                continue

            current_ports = get_current_excluded_ports(lambda_arn)
            if not current_ports:
                print("No hay puertos excluidos para eliminar")
                continue

            print("\nPuertos disponibles para eliminar:")
            print("-" * 50)
            for port in sorted(current_ports):
                print(f"Puerto: {port}")
            print("-" * 50)

            port = 0
            while not (1 <= port <= 65535):
                try:
                    port = int(input("\nIntroduce el número de puerto a eliminar: "))
                    if not (1 <= port <= 65535):
                        print("Error: El puerto debe estar entre 1 y 65535")
                        port = 0
                except ValueError:
                    print("Error: Introduce un número válido")
                    port = 0

            sns_arn = input("\nIntroduce el ARN del tema SNS: ").strip()
            if not sns_arn.startswith('arn:aws:sns:'):
                print("Error: El ARN debe comenzar con 'arn:aws:sns:'")
                continue

            if remove_excluded_port(lambda_arn, port, sns_arn):
                print("\n✅ Puerto eliminado exitosamente de las excepciones")
                print("✅ Notificación SNS enviada")
            else:
                print("\n❌ Error al eliminar el puerto")

        elif option == "4":
            print("\n¡Hasta luego!")
            break

        else:
            print("\nOpción no válida. Por favor, selecciona una opción válida (1-4)")

if __name__ == "__main__":
    main()
