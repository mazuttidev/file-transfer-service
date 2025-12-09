import socket
import os
import math
import random
import struct
import zlib

# Constantes
TAMANHO_CABECALHO = 8  # 4 bytes seq + 4 bytes checksum
TAMANHO_BUFFER_PADRAO = 1024
PORTA_PADRAO = 12000
PACOTE_FIM = (0, 0)


def calcular_checksum(dados):
    """Calcula o checksum CRC32 dos dados."""
    return zlib.crc32(dados)


def criar_cabecalho(numero_sequencia, checksum):
    """Cria o cabeçalho do pacote com número de sequência e checksum."""
    return struct.pack('!II', numero_sequencia, checksum)


def simular_perda_pacote(taxa_perda):
    """Verifica se o pacote deve ser perdido."""
    return random.random() < taxa_perda


def simular_erro_pacote(taxa_erro):
    """Verifica se o pacote deve ter erro."""
    return random.random() < taxa_erro


def corromper_dados(dados):
    """Corrompe aleatoriamente alguns bytes dos dados."""
    dados_lista = bytearray(dados)
    num_corrupcoes = random.randint(1, min(5, len(dados_lista)))
    
    for _ in range(num_corrupcoes):
        posicao = random.randint(0, len(dados_lista) - 1)
        dados_lista[posicao] = random.randint(0, 255)
    
    return bytes(dados_lista)


def enviar_pacote(socket_cliente, numero_sequencia, dados, checksum):
    """Envia um pacote com cabeçalho e dados."""
    cabecalho = criar_cabecalho(numero_sequencia, checksum)
    socket_cliente.send(cabecalho + dados)


def ler_e_armazenar_pacotes(arquivo, tamanho_buffer):
    """Lê o arquivo e armazena todos os pacotes em buffer."""
    buffer_pacotes = {}
    numero_sequencia = 0
    
    while (chunk := arquivo.read(tamanho_buffer)):
        numero_sequencia += 1
        checksum = calcular_checksum(chunk)
        buffer_pacotes[numero_sequencia] = (chunk, checksum)
    
    return buffer_pacotes


def processar_envio_inicial(socket_cliente, buffer_pacotes, taxa_perda, taxa_erro, num_total_pacotes):
    """Processa o envio inicial de todos os pacotes com simulação de erros e perdas."""
    total_enviados = 0
    total_perdidos = 0
    total_com_erro = 0
    
    for numero_seq, (dados, checksum) in buffer_pacotes.items():
        # Simula perda de pacote SOMENTE se taxa_perda > 0
        if taxa_perda > 0 and simular_perda_pacote(taxa_perda):
            total_perdidos += 1
            print(f'[PERDIDO] Pacote {numero_seq}/{num_total_pacotes} não foi enviado')
            continue
        
        # Verifica se deve corromper o pacote SOMENTE se taxa_erro > 0
        deve_corromper = taxa_erro > 0 and simular_erro_pacote(taxa_erro)
        
        if deve_corromper:
            dados_corrompidos = corromper_dados(dados)
            total_com_erro += 1
            print(f'[ERRO] Pacote {numero_seq}/{num_total_pacotes} enviado com dados corrompidos')
            enviar_pacote(socket_cliente, numero_seq, dados_corrompidos, checksum)
        else:
            print(f'[OK] Pacote {numero_seq}/{num_total_pacotes} enviado corretamente')
            enviar_pacote(socket_cliente, numero_seq, dados, checksum)
        
        total_enviados += 1
    
    # Sinaliza fim do envio inicial
    socket_cliente.send(struct.pack('!II', *PACOTE_FIM))
    
    return total_enviados, total_perdidos, total_com_erro


def processar_retransmissao(socket_cliente, buffer_pacotes, taxa_perda, taxa_erro, rodada):
    """Processa a fase de retransmissão de pacotes solicitados pelo servidor."""
    try:
        # Recebe número de pacotes a retransmitir
        dados = socket_cliente.recv(4)
        if not dados:
            print("Servidor não solicitou retransmissões")
            return True
        
        num_retransmissoes = struct.unpack('!I', dados)[0]
        
        if num_retransmissoes == 0:
            print("✓ Nenhum pacote precisa ser retransmitido!")
            return True
        
        print(f"Servidor solicitou retransmissão de {num_retransmissoes} pacote(s)")
        
        # Recebe lista de pacotes a retransmitir
        pacotes_retransmitir = []
        for _ in range(num_retransmissoes):
            dados = socket_cliente.recv(4)
            numero_seq = struct.unpack('!I', dados)[0]
            pacotes_retransmitir.append(numero_seq)
        
        print(f"Pacotes para retransmitir: {pacotes_retransmitir}")
        
        # Retransmite pacotes solicitados COM simulação de erros e perdas
        total_reenviados = 0
        total_perdidos_retrans = 0
        total_erro_retrans = 0
        
        for numero_seq in pacotes_retransmitir:
            if numero_seq not in buffer_pacotes:
                continue
            
            dados, checksum = buffer_pacotes[numero_seq]
            
            # Simula perda de pacote na retransmissão SOMENTE se taxa_perda > 0
            if taxa_perda > 0 and simular_perda_pacote(taxa_perda):
                total_perdidos_retrans += 1
                print(f'[PERDIDO] Pacote {numero_seq} não foi reenviado (perdido na retransmissão)')
                continue
            
            # Simula erro no pacote durante retransmissão SOMENTE se taxa_erro > 0
            deve_corromper = taxa_erro > 0 and simular_erro_pacote(taxa_erro)
            
            if deve_corromper:
                dados_corrompidos = corromper_dados(dados)
                total_erro_retrans += 1
                print(f'[ERRO] Pacote {numero_seq} reenviado com erro')
                enviar_pacote(socket_cliente, numero_seq, dados_corrompidos, checksum)
            else:
                print(f'[REENVIO] Pacote {numero_seq} retransmitido')
                enviar_pacote(socket_cliente, numero_seq, dados, checksum)
            
            total_reenviados += 1
        
        # Sinaliza fim das retransmissões
        socket_cliente.send(struct.pack('!II', *PACOTE_FIM))
        
        print(f"Rodada {rodada} - Reenviados: {total_reenviados}, Perdidos: {total_perdidos_retrans}, Com erro: {total_erro_retrans}")
        return False  # Retorna False para indicar que ainda não terminou (servidor deve verificar novamente)
    except socket.timeout:
        print('[TIMEOUT] Timeout esperando requisição de retransmissão do servidor')
        return True
    except Exception as e:
        print(f'[ERRO] Erro processando retransmissão: {e}')
        return True


def exibir_informacoes_iniciais(nome_arquivo, tamanho_arquivo, num_pacotes, taxa_perda, taxa_erro):
    """Exibe informações sobre o arquivo e configurações de transferência."""
    print(f"Arquivo: {nome_arquivo}")
    print(f"Tamanho total do arquivo: {tamanho_arquivo} bytes")
    print(f"Número total de pacotes a serem enviados: {num_pacotes}")
    print(f"Taxa de perda configurada: {taxa_perda*100}%")
    print(f"Taxa de erro configurada: {taxa_erro*100}%")
    print("-" * 50)


def exibir_resumo_envio(num_total, num_enviados, num_perdidos, num_erro):
    """Exibe resumo do envio inicial."""
    print("-" * 50)
    print("Envio inicial concluído!")
    print(f"Pacotes processados: {num_total}")
    print(f"Pacotes enviados: {num_enviados}")
    print(f"Pacotes perdidos (simulados): {num_perdidos}")
    print(f"Pacotes com erro (simulados): {num_erro}")


def enviar_arquivo(nome_arquivo, host, porta, tamanho_buffer=TAMANHO_BUFFER_PADRAO, 
                   taxa_perda=0.0, taxa_erro=0.0):
    """
    Envia um arquivo para o servidor usando protocolo de retransmissão.
    
    Args:
        nome_arquivo: Caminho do arquivo a ser enviado
        host: Endereço IP do servidor
        porta: Porta do servidor
        tamanho_buffer: Tamanho de cada pacote em bytes
        taxa_perda: Taxa de perda de pacotes (0.0 a 1.0)
        taxa_erro: Taxa de erro em pacotes (0.0 a 1.0)
    """
    if not os.path.exists(nome_arquivo):
        print(f"Erro: O arquivo {nome_arquivo} não foi encontrado.")
        return

    # Calcula informações do arquivo
    tamanho_arquivo = os.path.getsize(nome_arquivo)
    num_pacotes = math.ceil(tamanho_arquivo / tamanho_buffer)

    exibir_informacoes_iniciais(nome_arquivo, tamanho_arquivo, num_pacotes, taxa_perda, taxa_erro)

    # Conecta ao servidor
    socket_cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket_cliente.settimeout(10.0)  # Timeout de 10 segundos
    socket_cliente.connect((host, porta))

    # Envia o nome do arquivo (padded para TAMANHO_NOME_ARQUIVO bytes)
    TAMANHO_NOME_ARQUIVO = 1024
    nome_arquivo_bytes = nome_arquivo.encode('utf-8')
    nome_arquivo_padded = nome_arquivo_bytes.ljust(TAMANHO_NOME_ARQUIVO, b'\x00')
    socket_cliente.send(nome_arquivo_padded)
    
    # Envia o número total de pacotes (para que servidor saiba quantos esperar)
    socket_cliente.send(struct.pack('!I', num_pacotes))

    # Lê arquivo e armazena pacotes
    with open(nome_arquivo, 'rb') as arquivo:
        buffer_pacotes = ler_e_armazenar_pacotes(arquivo, tamanho_buffer)

    print("\n=== Envio Inicial com erros e perdas ===")
    total_enviados, total_perdidos, total_erro = processar_envio_inicial(
        socket_cliente, buffer_pacotes, taxa_perda, taxa_erro, num_pacotes
    )
    
    exibir_resumo_envio(num_pacotes, total_enviados, total_perdidos, total_erro)

    # Loop de retransmissão até completar
    print("\n=== Retransmissão ===")
    rodada = 1
    while True:
        concluido = processar_retransmissao(socket_cliente, buffer_pacotes, taxa_perda, taxa_erro, rodada)
        if concluido:
            break
        rodada += 1

    print("-" * 50)
    print(f"✓ Transferência finalizada! Total de rodadas: {rodada}")
    socket_cliente.close()


def obter_entrada_usuario():
    """Solicita e valida entradas do usuário."""
    ip_servidor = input("Digite o IP do servidor: ")
    caminho_arquivo = input("Digite o caminho completo do arquivo: ")
    
    try:
        taxa_perda = float(input("Digite a taxa de perda (0.0 a 1.0, ex: 0.1 para 10%): ") or "0.0")
        taxa_erro = float(input("Digite a taxa de erro (0.0 a 1.0, ex: 0.1 para 10%): ") or "0.0")
    except ValueError:
        print("Valores inválidos! Usando taxas padrão 0.0")
        taxa_perda = 0.0
        taxa_erro = 0.0
    
    return ip_servidor, caminho_arquivo, taxa_perda, taxa_erro


if __name__ == "__main__":
    ip, arquivo, perda, erro = obter_entrada_usuario()
    enviar_arquivo(arquivo, ip, PORTA_PADRAO, tamanho_buffer=128, 
                   taxa_perda=perda, taxa_erro=erro)
