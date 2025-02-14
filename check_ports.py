import boto3
import json
import argparse
import logging
from datetime import datetime

def setup_logger():
    """Configura el logger"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

def get_security_groups():
    """Obtiene y muestra todos los grupos de seguridad disponibles"""
    try:
        ec2 = boto3.client('ec2')
        response = ec2.describe_security_groups()
        groups = response['SecurityGroups']
        
        print("\nGrupos de seguridad disponibles:")
        print("-" * 50)
        for group in groups:
            print(f"ID: {group['GroupId']}")
            print(f"Nombre: {group['GroupName']}")
            print(f"Descripción: {group['Description']}")
            print("-" * 50)
        
        return groups
    except Exception as e:
        print(f"Error al obtener grupos de seguridad: {str(e)}")
        return None

def get_sns_topics():
    """Obtiene y muestra todos los temas SNS disponibles"""
    try:
        sns_client = boto3.client('sns')
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

def send_sns_notification(sns_arn, subject, message):
    """Envía una notificación SNS"""
    try:
        sns_client = boto3.client('sns')
        response = sns_client.publish(
            TopicArn=sns_arn,
            Subject=subject,
            Message=json.dumps(message, indent=2)
        )
        print(f"Notificación SNS enviada: {subject}")
        return response
    except Exception as e:
        print(f"Error enviando notificación SNS: {str(e)}")
        return None

def get_ports_from_user():
    """Solicita al usuario los puertos a excluir"""
    ports = set()
    print("\nIntroduce los puertos a excluir (uno por línea)")
    print("Deja la línea en blanco cuando hayas terminado")
    
    while True:
        try:
            port_input = input("Puerto (o Enter para terminar): ").strip()
            if not port_input:
                break
                
            port = int(port_input)
            if 1 <= port <= 65535:
                ports.add(port)
            else:
                print("Error: El puerto debe estar entre 1 y 65535")
        except ValueError:
            print("Error: Introduce un número válido")
    
    return ports

def check_security_group(group_id, excluded_ports, sns_arn):
    """Revisa y cierra puertos en un grupo de seguridad"""
    try:
        ec2 = boto3.client('ec2')
        
        # Obtener reglas del grupo de seguridad
        response = ec2.describe_security_groups(GroupIds=[group_id])
        security_group = response["SecurityGroups"][0]
        ingress_rules = security_group.get("IpPermissions", [])
        
        for rule in ingress_rules:
            # Verificar si la regla tiene un puerto específico
            if "FromPort" in rule and "ToPort" in rule:
                port = rule["FromPort"]
                
                # Saltar si el puerto está en la lista de excepciones
                if port in excluded_ports:
                    print(f"Saltando puerto {port} (excluido)")
                    continue
                
                # Verificar si el puerto está expuesto a Internet
                for ip_range in rule.get("IpRanges", []):
                    if ip_range.get("CidrIp") == "0.0.0.0/0":
                        # Revocar la regla
                        ec2.revoke_security_group_ingress(
                            GroupId=group_id,
                            IpPermissions=[{
                                "IpProtocol": rule["IpProtocol"],
                                "FromPort": port,
                                "ToPort": port,
                                "IpRanges": [{"CidrIp": "0.0.0.0/0"}]
                            }]
                        )
                        
                        message = {
                            "timestamp": datetime.now().isoformat(),
                            "action": "Puerto cerrado",
                            "security_group": group_id,
                            "port": port
                        }
                        
                        send_sns_notification(
                            sns_arn,
                            f"Puerto {port} cerrado en {group_id}",
                            message
                        )
                        
                        print(f"Puerto {port} cerrado en el grupo {group_id}")
        
        return True
    except Exception as e:
        print(f"Error procesando grupo de seguridad {group_id}: {str(e)}")
        return False

def main():
    # Configurar logger
    logger = setup_logger()
    
    # Mostrar grupos de seguridad disponibles
    security_groups = get_security_groups()
    if not security_groups:
        return
        
    # Mostrar temas SNS disponibles
    sns_topics = get_sns_topics()
    if not sns_topics:
        return
    
    # Solicitar grupo de seguridad
    group_id = input("\nIntroduce el ID del grupo de seguridad: ").strip()
    
    # Solicitar ARN del SNS
    sns_arn = input("\nIntroduce el ARN del tema SNS: ").strip()
    
    # Solicitar puertos a excluir
    excluded_ports = get_ports_from_user()
    
    print("\nResumen:")
    print(f"Grupo de seguridad: {group_id}")
    print(f"Topic SNS: {sns_arn}")
    print(f"Puertos excluidos: {excluded_ports}")
    
    confirm = input("\n¿Confirmar la operación? (s/n): ").lower()
    if confirm != 's':
        print("\nOperación cancelada")
        return
    
    if check_security_group(group_id, excluded_ports, sns_arn):
        print("\n✅ Revisión de puertos completada")
    else:
        print("\n❌ Error al revisar los puertos")

if __name__ == "__main__":
    main()
