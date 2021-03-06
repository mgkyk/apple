"""
this is the logic of the server
# Log: login, get the privilege
# MachineList: all the info of the Machine
# Machine: a Single Machine
# MachineList_Source: source for the MachineList
# Machine_Source: source for the singe Machine

# author: ChuXiaokai
# date: 2016/3/24
"""

from flask import Flask, request, jsonify
from flask.ext.httpauth import HTTPBasicAuth
from flask.ext.sqlalchemy import SQLAlchemy
import server

# server point
host = server.Server()
auth = HTTPBasicAuth()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///webappdb'
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
db = SQLAlchemy(app)

### database ###########################################################################
# table User
class User(db.Model):
    user = db.Column(db.String(40), primary_key=True)
    passwd = db.Column(db.String(40))
    num_mcs = db.Column(db.Integer)

    def __init__(self, user, passwd):
        self.user = user
        self.passwd = passwd
        self.num_mcs = 0

    def __repr__(self):
        return '<User %r>' % self.user


# table VM_machine
class VM_machine(db.Model):
    mc_id = db.Column(db.String(40), primary_key=True)
    user = db.Column(db.String(40))
    connect_info = db.Column(db.String(100))

    def __init__(self, mc_id, user, connect_info):
        self.mc_id = mc_id
        self.connect_info = connect_info
        self.user = user

    def __repr__(self):
        return '<mc_id %r>' % self.mc_id


# table Resource
class Resource(db.Model):
    source_name = db.Column(db.String(40), primary_key=True)
    map = db.Column(db.String(40))
    shell_path = db.Column(db.String(100))
    detail = db.Column(db.String(100))

    def __init__(self, source_name, map, shell_path, detail):
        self.source_name = source_name
        self.map = map
        self.shell_path = shell_path
        self.detail = detail

    def __repr__(self):
        return '<source_name %r>' % self.source_name

########################################################################################
### web app ############################################################################

@auth.verify_password
def verify_password(username_or_token, password):
    print("dddddddddddddddddddddddddddddddddddddddddddddddddd")
    if username_or_token == 'cxk':
        return False
    else:
        return True


# get a new user id
@app.route('/newuser', methods=['POST'])
def post_newuser():
    user = request.form['user']
    passwd = request.form['passwd']
    new_user = User(user, passwd)  # append a recode
    db.session.add(new_user)
    db.session.commit()
    return (jsonify({'user': new_user.user}))


# get a user info
@app.route('/<string:user_id>', methods=['GET'])
def get_user_info(user_id):
    admin = User.query.filter_by(user=user_id).first()
    return (jsonify({'userinfo': [{'user_id':admin.user}, {'num_mcs':admin.num_mcs}]}))


# get a new mc
@app.route('/<string:user_id>', methods=['POST'])
def get_new_mc(user_id):
    mc_id, passwd, mc_ip = host.init_machine()
    connect_info =  'host: %s  passwd: %s  machine_ip: %s' % (host.ip, passwd, mc_ip)
    new_mc = VM_machine(mc_id, user_id, connect_info)
    db.session.add(new_mc)
    db.session.query(User).filter(User.user==user_id).update({User.num_mcs:User.num_mcs+1})
    db.session.commit()
    return (jsonify({'mc_info': [{'mc_info': mc_id, 'ip': mc_ip, 'passwd': passwd}]}))


# get user's mc list
@app.route('/<string:user_id>/mcs', methods=['GET'])
def get_machine_list(user_id):
    a = db.session.query(VM_machine).filter(VM_machine.user==user_id).all()
    user_machines = []
    print(type(a))
    for i in range(len(a)):
        print(i)
        print(a[i].mc_id)
        tmp = {"mc_id": a[i].mc_id, "user": a[i].user, "connect_info": a[i].connect_info}
        user_machines.append(tmp)
    return (jsonify({'user_machines': user_machines}))


# get user's a mc info
@app.route('/<string:user_id>/<string:mc_id>', methods=['GET'])
def get_machine(user_id, mc_id):
    mc_info = db.session.query(VM_machine).filter(VM_machine.user==user_id and VM_machine.mc_id == mc_id).first()
    return (jsonify({'machine_info': [{"mc_id": mc_info.mc_id, "user": mc_info.user, "connect_info": mc_info.connect_info}]}))


# delete user's a mc
@app.route('/<string:user_id>/<string:mc_id>', methods=['DELECT'])
def delect_machine(user_id, mc_id):
    host.kill_machine(mc_id)  # kill a mc
    # delete it in the database
    recode = db.session.query(VM_machine).filter(VM_machine.mc_id == mc_id).first()
    db.session.delete(recode)
    # update user information
    db.session.query(User).filter(User.user==user_id).update({User.num_mcs:User.num_mcs-1})
    return (jsonify({'state': 'current'"delete '%s' successfully !" % mc_id}))


# get resource list
@app.route('/srclist', methods=['GET'])
def get_source_list():
    recodes = db.session.query(Resource).all()
    sources_info = []
    for i in range(len(recodes)):
        tmp = {'source_name': recodes[i].source_name, 'detail': recodes[i].detail}
        sources_info.append(tmp)
    return (jsonify({'Sources Available': sources_info}))


# get a resource info
@app.route('/srclist/<string:src_name>', methods=['GET'])
def get_source(src_name):
    recode = db.session.query(Resource).filter(Resource.source_name==src_name).first()
    return (jsonify({'source_info': [{'source_name': recode.source_name, 'detail': recode.detail}]}))


# install a resource in a mc
@app.route('/srclist/<string:user_id>/<string:src_name>', methods=['POST'])
def install_source(user_id, src_name):
    def filter_space(x):  # this func f(x) is used for the filter
            if x != [] and x != " ":
                return x
        
    form = request.form['form']
    mc = request.form['mc']
    print(form, mc)
    # get the shell path
    recode = db.session.query(Resource).filter(Resource.source_name == src_name).first()
    shell_path = recode.shell_path
    # execute the shell
    if form == 'cluster':
        mc_param = mc.split(' ')
        mc_param = [item for item in filter(filter_space, mc_param)]  # filter the [] in mc_param
        if host.exec_shell(shell_path=shell_path, param=mc_param, state='cluster') == True: # install a cluster
            return (jsonify({'state': "Success install"}))
        else:
            return (jsonify({'state': "Fail to install"}))
    elif form == 'single_node':
        mc_param = mc
        print(mc_param)
        if host.exec_shell(shell_path=shell_path, param=mc_param, state='single') == True:  # install a single node
            return (jsonify({'state': "Success install"}))
        else:
            return (jsonify({'state': "Fail to install"}))



if __name__ == '__main__':
    db.create_all()
    app.run()
