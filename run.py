import os
import sys
sys.path.insert(0, '.')
from app import create_app, db
from app.models.models import Usuario, Setor
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

load_dotenv()

app = create_app()

with app.app_context():
    db.create_all()
    if not Usuario.query.filter_by(login='admin').first():
        admin = Usuario(
            nome='Administrador',
            login='admin',
            senha=generate_password_hash('Admin@123'),
            papel='admin'
        )
        db.session.add(admin)
        print('Usuario admin criado! Senha: Admin@123')
    else:
        admin = Usuario.query.filter_by(login='admin').first()
        if not admin.papel:
            admin.papel = 'admin'
            print('Papel admin atualizado!')
    if not Setor.query.first():
        for s in ['Estoque', 'PDV', 'Compras', 'Financeiro', 'Fiscal', 'RH', 'Contabilidade']:
            db.session.add(Setor(nome=s))
        print('Setores criados!')
    from app.contabilidade.seed import seed_plano_contas
    qtd = seed_plano_contas()
    if qtd:
        print(f'Plano de contas populado: {qtd} contas criadas!')
    db.session.commit()

if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug)
