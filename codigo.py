from flask import Flask, jsonify, request
import logging, psycopg2, time
import jwt
import bcrypt


from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    get_jwt_identity
)


def desencripta_pal(palavra):
    m=''
    for char in palavra:
        m+=chr(ord(char)-3)  
    return m


def desencripta(nome_fich):
    m=[]
    fich=open(nome_fich,'r')
    linhas=fich.readlines()
    for palavra in linhas:
        m.append(desencripta_pal(palavra.rstrip()))
    fich.close()    
    return m


app = Flask(__name__) 
app.config['JWT_SECRET_KEY'] = desencripta_pal('fkdyh_vhfuhwd')
jwt = JWTManager(app)


def db_connection():
    aux=desencripta('config.txt')
    db = psycopg2.connect(user = aux[0],
                            password = aux[1],
                            host = aux[2],
                            database = aux[3])  
    return db 


@app.route("/dbproj/user", methods=['POST'])
def registo_utilizadores():
    payload = request.get_json()

    conn = db_connection()
    cur = conn.cursor()
    
    if not payload:
            return jsonify('Body vazio')
    try:
        cur.execute("begin")   
        statement = """
                      INSERT INTO utilizador (username, password, email) 
                              VALUES (  %s ,   %s, %s )"""
    
        values = (payload["username"], payload["password"], payload["email"])  
        cur.execute(statement, values)
        #time.sleep(8)
        cur.execute("commit")
        cur.execute("select userid from utilizador where username=%s",(payload["username"],))
        row=cur.fetchall()
        x=row[0][0]
        result = {"userID":  x}
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)
        result = {"erro":  str(error)}
    finally:
        if conn is not None:
            conn.close()

    conn.close()
    return jsonify(result)


@app.route("/dbproj/user", methods=['PUT'])
def autenticacao_utilizadores():
    payload = request.get_json()
    
    conn = db_connection()
    cur = conn.cursor()
     
    if not payload:
            return jsonify('Body vazio')
    
    statement = """
                  SELECT userid, username, password FROM utilizador WHERE username= %s AND password = %s 
                          """

    values = (payload["username"], payload["password"])

    try:
        cur.execute(statement, values)
        rows = cur.fetchall()
        if not rows:
            result = {"erro":"Erro de autenticacao"}
        else:
            cur.execute("commit")
            access_token = create_access_token(identity={"userid": rows[0][0]})
            result = {"authToken":  access_token}
      
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)
        result = {"erro":  str(error)}
    finally:
        if conn is not None:
            conn.close()
                 
    conn.close()
    return jsonify(result)


@app.route("/dbproj/leilao", methods=['POST'])
@jwt_required()
#http://127.0.0.1:5000/dbproj/leilao
def criar_novo_leilao():
    payload = request.get_json()   
    user = get_jwt_identity()
    conn = db_connection()
    cur = conn.cursor()

    if not payload:
            return jsonify('body vazio')

    try:
        cur.execute("begin")
        statement = """INSERT INTO leilao_artigo (horatermino, titulo,artigo_ean,artigo_precomin, artigo_descricao, utilizador_userid) 
                              VALUES ( %s, %s, %s, %s, %s, %s )"""
    
        values = (payload["datetime"], payload["titulo"], payload["artigoId"], payload["precoMinimo"], payload["descricao"], user["userid"])        
        cur.execute(statement, values)
        #time.sleep(8)
        cur.execute("commit")
        cur.execute("select leilaoid from leilao_artigo where artigo_ean=%s",(payload["artigoId"],))
        row=cur.fetchall()
        x=row[0][0]        
        result = {"leiaoId":  x}
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)
        result = {"erro":  str(error)}
    finally:
        if conn is not None:
            conn.close()
         

    conn.close()
    return jsonify(result)


#http://127.0.0.1:5000/dbproj/utilizador
@app.route("/dbproj/leiloes", methods=['GET'], strict_slashes=True)
@jwt_required()
def listar_todos_leiloes_existentes():
    conn = db_connection()
    cur=conn.cursor()
    cur.execute("SELECT  artigo_descricao,leilaoId from leilao_artigo")
    rows = cur.fetchall()
    payload = []
    for row in rows:
        logger.debug(row)
        content = { 'descricao': row[0], 'leilaoId':int(row[1])}
        payload.append(content) # appending to the payload to be returned

    conn.close()
    return jsonify(payload)    


#lista todos os leiloes com a keyword correspondente
#http://127.0.0.1:5000/dbproj/utilizador
@app.route("/dbproj/leiloes/<keyword>", methods=['GET'], strict_slashes=True)
@jwt_required()
def pesquisar_leiloes_existentes(keyword):
    conn = db_connection()
    cur = conn.cursor()
    content = "N„o h· leilıes correspondentes"
    try:
        int(keyword) #try cast if fails get exception and assume its a description
        cur.execute("SELECT  artigo_descricao,leilaoId from leilao_artigo where leilaoativo = true and artigo_ean = %s", (keyword,) )
        rows = cur.fetchall()
        payload = []
        for row in rows:
            logger.debug(row)
            content = { 'descricao': row[0], 'leilaoId':int(row[1])}
            payload.append(content) # appending to the payload to be returned
        
    except ValueError:
        cur.execute("SELECT  artigo_descricao,leilaoId from leilao_artigo where leilaoativo = true and artigo_descricao = %s", (keyword,) )
        rows = cur.fetchall()
        payload = []
        for row in rows:
            logger.debug(row)
            content = { 'descricao': row[0], 'leilaoId':int(row[1])}
            payload.append(content) # appending to the payload to be returned

    conn.close ()
    return jsonify(content) 
    
    
#lista detalhes de leilao com leilaoId correspondente
#http://127.0.0.1:5000/dbproj/utilizador
@app.route("/dbproj/leilao/<leilaoId>", methods=['GET'], strict_slashes=True)
@jwt_required()
def consultar_detalhes_leilao(leilaoId):
    conn = db_connection()
    cur = conn.cursor()
    payload = "Nao ha leiloes correspondentes"
    try:
        int(leilaoId) #try cast if fails get exception and assume its a description
        cur.execute("select artigo_descricao, horatermino from leilao_artigo  where leilaoid = %s", (leilaoId,) )
        rows = cur.fetchall()
        if(len(rows)==0):
            return jsonify(payload)
        payload = []
        for row in rows:
            logger.debug(row)
            content = { 'leilaoId': leilaoId,'descricao': row[0], 'hora de termino':row[1]}
            payload.append(content) # appending to the payload to be returned
            
        cur.execute("select  utilizador_userid,text from mensagem where leilao_artigo_leilaoid = %s", (leilaoId,) )
        rows = cur.fetchall()
        mural = {'Mural ': ''}
        payload.append(mural)
        for row in rows:
            logger.debug(row)
            content = { 'userId': int(row[0]),'texto': row[1]}
            payload.append(content) # appending to the payload to be returned
            
        cur.execute("select  utilizador_userid,valor from licitacao where leilao_artigo_leilaoid = %s order by valor asc", (leilaoId,) )
        rows = cur.fetchall()
        mural = {'Licitacoes ': ''}
        payload.append(mural)
        for row in rows:
            logger.debug(row)
            content = { 'userId': int(row[0]),'valor': int(row[1])}
            payload.append(content) # appending to the payload to be returned
        
    except ValueError:
        payload = "leilaoID inv·lido, n„o È um inteiro"

    conn.close ()
    return jsonify(payload) 



#http://127.0.0.1:5000/dbproj/leiloes_utilizador
@app.route("/dbproj/leiloes_utilizador", methods=['GET'], strict_slashes=True)
@jwt_required()
def listar_leiloes_de_utilizador():
    conn = db_connection()
    cur = conn.cursor()
    payload = "N„o existem leilıes que correspondam a este utilizador"
    try:
        user = get_jwt_identity()
        cur.execute("begin")
        cur.execute("select leilaoid,artigo_descricao from leilao_artigo where utilizador_userid=%s",[user["userid"]])
        rows = cur.fetchall()
        if(len(rows)!=0):
            payload = []
            payload.append({'Criador':''})
        for row in rows:
            logger.debug(row)
            content = { 'leilaoId': row[0],'descricao': row[1]}
            payload.append(content) # appending to the payload to be returned

            
           
        cur.execute("select distinct(l.leilaoid),l.artigo_descricao from leilao_artigo as l,licitacao as h where h.utilizador_userid=%s and l.leilaoid=h.leilao_artigo_leilaoid;",[user["userid"]])
        rows = cur.fetchall()
        if(len(rows)!=0):
            if(payload=="N„o existem leilıes que correspondam a este utilizador"):
                payload=[]
            payload.append({'Licitador':''})
        for row in rows:
            logger.debug(row)
            content = { 'leilaoId': row[0],'descricao': row[1]}
            payload.append(content) # appending to the payload to be returned
        
    except ValueError:
        payload = "leilaoID inv√°lido, n√£o √© um inteiro"

    conn.close ()
    return jsonify(payload) 


@app.route("/dbproj/licitar/<leilaoId>/<licitacao>", methods=['GET'], strict_slashes=True)
@jwt_required()
def efetuar_licitacao(leilaoId,licitacao):
    conn = db_connection()
    cur=conn.cursor()
    
    payload=[]
    user = get_jwt_identity()
    cur.execute("select func_licitacao( %s, %s, %s)", (user["userid"],licitacao,leilaoId,))
    row=cur.fetchall()
    cur.execute("commit")
 
    payload.append(row[0]) # appending to the payload to be returned    
    
    conn.close()
    return jsonify(payload)     


@app.route("/dbproj/leilao/<leilaoId>", methods=['PUT'], strict_slashes=True)
@jwt_required()
def editar_propriedades_leilao(leilaoId):
    conn = db_connection()
    cur=conn.cursor()
    
    payload = request.get_json()
    user = get_jwt_identity()

    
    if not payload:
            return jsonify('Body vazio')
        
    if 'descricao' not in payload:
        cur.execute("select func_edicao( %s, %s, %s, %s)", (payload["titulo"], 'null',leilaoId,user["userid"]))
        row=cur.fetchall()
        cur.execute("commit")
    
    elif 'titulo' not in payload:
        cur.execute("select func_edicao(%s,%s,%s,%s)", ('null', payload["descricao"],leilaoId, user["userid"]))
        row=cur.fetchall()
        cur.execute("commit")
    else:
        cur.execute("select func_edicao( %s, %s, %s, %s)", (payload["titulo"], payload["descricao"],leilaoId,user["userid"]))
        row=cur.fetchall()
        cur.execute("commit")
    
    payload=[]
    payload.append(row[0]) # appending to the payload to be returned    

    if(row == [('1',)]):
        cur.execute('select * from leilao_artigo where leilaoid = (select max(leilaoid) from leilao_artigo)')
        row=cur.fetchall()
        row=row[0]
        payload=[]
        content = { 'leilaoId': row[0],'horatermino': row[1],'titulo': row[2], 'maiorprecolicitado': row[3], 'leilaoativo': row[4],'leilaocancelado': row[5],'artigoean': row[6], 'artigoprecominimo': row[7], 'artigo_descricao': row[8],'utilizador_userid': row[9]}
        payload.append(content) # appending to the payload to be returned
        
        
    conn.close()
    return jsonify(payload)   


@app.route("/dbproj/mensagem/<leilaoId>", methods=['POST'])
@jwt_required()
def escrever_mensagem(leilaoId): 
    payload = request.get_json()
    user = get_jwt_identity()
    conn = db_connection()
    cur = conn.cursor()
    
    if not payload:
            return jsonify('body vazio')
    try:
        print(payload)
        cur.execute("begin") 
        statement = """
                      INSERT INTO mensagem (text, leilao_artigo_leilaoid, utilizador_userid) 
                              VALUES ( %s, %s, %s )"""
    
        values = (payload["mensagem"], leilaoId, user["userid"]) 
        cur.execute(statement, values)
        #time.sleep(8)
        cur.execute("commit")
        result = "Mensagem inserida com sucesso!"
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)
        result = {"erro":  str(error)}
    finally:
        if conn is not None:
            conn.close()
         
    conn.close()
    return jsonify(result)


@app.route("/dbproj/terminar_leiloes/", methods=['GET'], strict_slashes=True)
@jwt_required()
def terminar_leiloes():
    conn = db_connection()
    cur=conn.cursor()

    cur.execute("call terminar_leiloes()")  
    cur.execute("commit")
    
    conn.close()
    return jsonify("leiloes terminados")




@app.route("/dbproj/notificacoes", methods=['GET'], strict_slashes=True)
@jwt_required()
def listar_notificacoes():
    conn = db_connection()
    cur=conn.cursor()
    user = get_jwt_identity()
    cur.execute("SELECT text from notificacoes where utilizador_userid=%s", ([user["userid"]]))
    rows = cur.fetchall()
    print(rows)
    payload = []
    
    for row in rows:
        logger.debug(row)
        content = { 'text': row[0] }
        print(content)
        payload.append(content) # appending to the payload to be returned

    conn.close()
    return jsonify(payload)  


@app.route("/dbproj/edicoes/<leilaoId>", methods=['GET'], strict_slashes=True)
@jwt_required()
def listar_edicoes(leilaoId):
    conn = db_connection()
    cur=conn.cursor()
    user = get_jwt_identity()
    cur.execute("SELECT titulo, descricao, leilao_editado.leilao_artigo_leilaoid  from leilao_editado where leilao_editado.leilao_artigo_leilaoid=%s", (leilaoId,) )
    rows = cur.fetchall()
    if not rows:
        payload="Nao ha leiloes correspondentes"
    else:
        payload = []
        for row in rows:
            logger.debug(row)
            content = { 'titulo': row[0],'descricao':row[1]}
            payload.append(content) # appending to the payload to be returned

    conn.close()
    return jsonify(payload)



if __name__ == "__main__":
    # Set up the logging
    logger = logging.getLogger('logger')
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    
        # create formatter
    formatter = logging.Formatter('%(asctime)s [%(levelname)s]:  %(message)s',
                                  '%H:%M:%S')
                                  # "%Y-%m-%d %H:%M:%S") # not using DATE to simplify
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    
    time.sleep(1) # just to let the DB start before this print :-)

    
    logger.info("\n---------------------------------------------------------------\n" + 
                          "API online: http://127.0.0.1:5000/dbproj/\n\n")    
        
    
    app.run(host="127.0.0.1", debug=False, threaded=True)    
    conn=db_connection()
