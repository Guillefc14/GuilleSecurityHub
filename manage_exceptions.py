import boto3
import json
import argparse

# Nombre de la función Lambda
LAMBDA_FUNCTION_NAME = "Cierra-Puertos"
SNS_TOPIC_ARN = "arn:aws:sns:eu-west-3:061039770309:Puerto-Ok"

# Inicializar clientes
lambda_client = boto3.client('lambda')
sns_client = boto3.client('sns')

def get_current_excluded_ports():
    try:
        response = lambda_client.get_function(FunctionName=LAMBDA_FUNCTION_NAME)
        lambda_config = response['Configuration']
        environment = lambda_config.get('Environment', {})
        env_vars = environment.get('Variables', {})
        excluded_ports = env_vars.get('EXCLUDED_PORTS', '{80, 443}')
        return eval(excluded_ports)
    except Exception as e:
        print(f"Error al obtener puertos excluidos: {str(e)}")
        return set()

def update_excluded_ports(new_port, description):
    try:
        current_ports = get_current_excluded_ports()
        current_ports.add(new_port)
        
        response = lambda_client.update_function_configuration(
            FunctionName=LAMBDA_FUNCTION_NAME,
            Environment={
                'Variables': {
                    'EXCLUDED_PORTS': str(current_ports)
                }
            }
        )
        
        message = {
            "accion": "Puerto añadido a excepciones",
            "puerto": new_port,
            "descripcion": description,
            "puertos_excluidos_actuales": list(current_ports)
        }
        
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f"Nuevo puerto ({new_port}) añadido a excepciones",
            Message=json.dumps(message, indent=2)
        )
        
        return True
    except Exception as e:
        print(f"Error al actualizar puertos excluidos: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Añadir puerto a excepciones')
    parser.add_argument('--port', type=int, required=True, help='Puerto a excluir')
    parser.add_argument('--description', type=str, required=True, help='Descripción de la excepción')
    parser.add_argument('--force', action='store_true', help='No pedir confirmación')
    
    args = parser.parse_args()
    
    if not 1 <= args.port <= 65535:
        print("Error: El puerto debe estar entre 1 y 65535")
        return

    current_ports = get_current_excluded_ports()
    print(f"\nPuertos actualmente excluidos: {current_ports}")
    
    if args.port in current_ports:
        print(f"\nEl puerto {args.port} ya está en la lista de excepciones")
        return
    
    print("\nResumen:")
    print(f"Puerto a excluir: {args.port}")
    print(f"Descripción: {args.description}")
    
    if not args.force:
        confirm = input("\n¿Confirmar la acción? (s/n): ").lower()
        if confirm != 's':
            print("\nOperación cancelada")
            return
    
    if update_excluded_ports(args.port, args.description):
        print("\n✅ Puerto añadido exitosamente a las excepciones")
        print("✅ Notificación SNS enviada")
        print(f"✅ Nuevos puertos excluidos: {get_current_excluded_ports()}")
    else:
        print("\n❌ Error al añadir el puerto")

if __name__ == "__main__":
    main()
