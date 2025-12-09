import socket
import struct
import zlib

# Constantes
TAMANHO_CABECALHO = 8  # 4 bytes seq + 4 bytes checksum
TAMANHO_BUFFER_PADRAO = 1024
PORTA_PADRAO = 12000
TAMANHO_NOME_ARQUIVO = 1024


def calcular_checksum(dados):
    """Calcula o checksum CRC32 dos dados."""
    return zlib.crc32(dados)


def extrair_cabecalho(dados):
    """Extrai número de sequência e checksum do cabeçalho do pacote."""
    numero_sequencia = struct.unpack('!I', dados[:4])[0]
    checksum_recebido = struct.unpack('!I', dados[4:8])[0]
    return numero_sequencia, checksum_recebido


def validar_checksum(dados, checksum_esperado):
    """Valida se o checksum dos dados corresponde ao esperado."""
    checksum_calculado = calcular_checksum(dados)
    return checksum_calculado == checksum_esperado


def receber_pacotes_iniciais(conexao, tamanho_pacote, num_pacotes_esperados):
    """
    Recebe e valida todos os pacotes da transmissão inicial.
    
    Args:
        num_pacotes_esperados: Número total de pacotes que o cliente vai enviar
    
    Returns:
        Tupla contendo (pacotes_validos, numero_sequencia_maximo)
    """
    pacotes_validos = {}
    numero_seq_maximo_recebido = 0
    
    while True:
        try:
            dados = conexao.recv(tamanho_pacote)
            if not dados or len(dados) < TAMANHO_CABECALHO:
                break
            
            numero_seq, checksum_recebido = extrair_cabecalho(dados)
            
            # Pacote com seq 0 sinaliza fim do envio
            if numero_seq == 0:
                break
            
            # Pego dados apenas depois do cabeçalho
            payload = dados[TAMANHO_CABECALHO:]
            
            # Valida checksum
            if validar_checksum(payload, checksum_recebido):
                pacotes_validos[numero_seq] = payload
                print(f'[OK] Pacote {numero_seq} recebido e validado ({len(payload)} bytes)')
            else:
                print(f'[ERRO] Pacote {numero_seq} com checksum inválido - será solicitado reenvio')
            
            if numero_seq > numero_seq_maximo_recebido:
                numero_seq_maximo_recebido = numero_seq
        except socket.timeout:
            print('[TIMEOUT] Timeout esperando pacotes iniciais')
            break
        except Exception as e:
            print(f'[ERRO] Erro recebendo pacote: {e}')
            break
    
    # Retorna número esperado (não o máximo recebido) para detectar pacotes finais perdidos
    return pacotes_validos, num_pacotes_esperados


def detectar_pacotes_ausentes(pacotes_validos, numero_seq_maximo):
    """Detecta quais pacotes estão faltando ou corrompidos."""
    sequencia_esperada = range(1, numero_seq_maximo + 1)
    pacotes_ausentes = sorted(set(sequencia_esperada) - set(pacotes_validos.keys()))
    return pacotes_ausentes


def exibir_resumo_inicial(pacotes_validos, numero_seq_maximo, pacotes_ausentes):
    """Exibe resumo da fase inicial."""
    print("-" * 50)
    print("Fase inicial concluída!")
    print(f"Pacotes válidos recebidos: {len(pacotes_validos)}/{numero_seq_maximo}")
    
    if pacotes_ausentes:
        print(f"Pacotes perdidos ou com erro: {pacotes_ausentes}")
        print(f"Total de pacotes a retransmitir: {len(pacotes_ausentes)}")
    else:
        print("Todos os pacotes recebidos corretamente!")


def solicitar_retransmissao(conexao, pacotes_ausentes):
    """Envia solicitação de retransmissão ao cliente."""
    # Envia número de pacotes a retransmitir
    conexao.send(struct.pack('!I', len(pacotes_ausentes)))
    
    if not pacotes_ausentes:
        return
    
    # Envia lista de números de sequência
    for numero_seq in pacotes_ausentes:
        conexao.send(struct.pack('!I', numero_seq))
    
    print(f"Solicitada retransmissão de {len(pacotes_ausentes)} pacote(s)")


def receber_retransmissoes(conexao, tamanho_pacote, pacotes_validos):
    """Recebe e valida pacotes retransmitidos."""
    while True:
        try:
            dados = conexao.recv(tamanho_pacote)
            if not dados or len(dados) < TAMANHO_CABECALHO:
                break
            
            numero_seq, checksum_recebido = extrair_cabecalho(dados)
            
            # Pacote com seq 0 sinaliza fim das retransmissões
            if numero_seq == 0:
                break
            
            payload = dados[TAMANHO_CABECALHO:]
            
            if validar_checksum(payload, checksum_recebido):
                pacotes_validos[numero_seq] = payload
                print(f'[REENVIO OK] Pacote {numero_seq} retransmitido e validado')
            else:
                print(f'[REENVIO ERRO] Pacote {numero_seq} ainda com erro')
        except socket.timeout:
            print('[TIMEOUT] Timeout esperando retransmissões')
            break
        except Exception as e:
            print(f'[ERRO] Erro recebendo retransmissão: {e}')
            break


def montar_arquivo(nome_arquivo, pacotes_validos):
    """Monta o arquivo final ordenando os pacotes por número de sequência."""
    with open(nome_arquivo, 'wb') as arquivo:
        total_bytes = 0
        for numero_seq in sorted(pacotes_validos.keys()):
            arquivo.write(pacotes_validos[numero_seq])
            total_bytes += len(pacotes_validos[numero_seq])
    
    return total_bytes


def exibir_resultado_final(nome_arquivo, pacotes_validos, total_bytes, numero_seq_maximo):
    """Exibe resultado final da transferência."""
    print(f"Arquivo {nome_arquivo} salvo!")
    print(f"Total de pacotes finais: {len(pacotes_validos)}")
    print(f"Tamanho total: {total_bytes} bytes")
    
    if len(pacotes_validos) == numero_seq_maximo:
        print("✓ Transferência completa - todos os pacotes recebidos!")
    else:
        pacotes_faltantes = numero_seq_maximo - len(pacotes_validos)
        print(f"⚠ ATENÇÃO: Faltam {pacotes_faltantes} pacote(s)")


def iniciar_servidor(host, porta, tamanho_buffer=TAMANHO_BUFFER_PADRAO):
    """
    Inicia o servidor para receber arquivos com protocolo de retransmissão.
    
    Args:
        host: Endereço IP do servidor
        porta: Porta para escutar conexões
        tamanho_buffer: Tamanho máximo de dados por pacote
    """
    tamanho_pacote = tamanho_buffer + TAMANHO_CABECALHO
    
    # Configura socket do servidor
    socket_servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket_servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    socket_servidor.bind((host, porta))
    socket_servidor.listen(1)
    
    print(f"Servidor ouvindo em {host}:{porta}...")
    print("-" * 50)

    # Aceita conexão
    conexao, endereco = socket_servidor.accept()
    conexao.settimeout(5.0)  # Timeout de 5 segundos para evitar bloqueios
    print(f"Conexão estabelecida com {endereco}")

    # Recebe nome do arquivo
    nome_arquivo = conexao.recv(TAMANHO_NOME_ARQUIVO).decode('utf-8').rstrip('\x00')
    print(f"Recebendo arquivo: {nome_arquivo}")
    
    # Recebe número total de pacotes esperados
    dados_num_pacotes = conexao.recv(4)
    num_pacotes_total = struct.unpack('!I', dados_num_pacotes)[0]
    print(f"Total de pacotes esperados: {num_pacotes_total}")
    print("-" * 50)

    # FASE 1: Recepção inicial
    print("\n=== Recepção Inicial ===")
    pacotes_validos, numero_seq_maximo = receber_pacotes_iniciais(conexao, tamanho_pacote, num_pacotes_total)
    
    # Detecta pacotes ausentes
    pacotes_ausentes = detectar_pacotes_ausentes(pacotes_validos, numero_seq_maximo)
    exibir_resumo_inicial(pacotes_validos, numero_seq_maximo, pacotes_ausentes)
    
    # Loop de retransmissão até receber todos os pacotes
    print("\n=== Solicitação de Retransmissão ===")
    rodada = 1
    
    while pacotes_ausentes:
        print(f"\n--- Rodada {rodada} ---")
        solicitar_retransmissao(conexao, pacotes_ausentes)
        receber_retransmissoes(conexao, tamanho_pacote, pacotes_validos)
        
        # Verifica novamente se ainda faltam pacotes
        pacotes_ausentes = detectar_pacotes_ausentes(pacotes_validos, numero_seq_maximo)
        
        if pacotes_ausentes:
            print(f"Ainda faltam {len(pacotes_ausentes)} pacote(s): {pacotes_ausentes}")
            rodada += 1
        else:
            print("✓ Todos os pacotes recebidos!")
    
    # Se não havia pacotes ausentes desde o início
    if rodada == 1 and not pacotes_ausentes:
        solicitar_retransmissao(conexao, pacotes_ausentes)
    
    print(f"\nTotal de rodadas de retransmissão: {rodada}")
    print("-" * 50)
    
    # Monta arquivo final
    print("\n=== Montando arquivo final ===")
    total_bytes = montar_arquivo(nome_arquivo, pacotes_validos)
    exibir_resultado_final(nome_arquivo, pacotes_validos, total_bytes, numero_seq_maximo)

    # Fecha conexões
    conexao.close()
    socket_servidor.close()


if __name__ == "__main__":
    ip_servidor = input("Digite o IP deste servidor: ")
    iniciar_servidor(ip_servidor, PORTA_PADRAO, tamanho_buffer=128)
