class DatabaseRouter:
    """
    A router to control all database operations on models in the
    microservices application.
    """
    
    def db_for_read(self, model, **hints):
        """Suggest the database for read operations."""
        if model._meta.app_label == 'users':
            return 'users_db'
        elif model._meta.app_label == 'shifting':
            return 'shifting_db'
        elif model._meta.app_label == 'analytics':
            return 'analytics_db'
        return 'default'
    
    def db_for_write(self, model, **hints):
        """Suggest the database for write operations."""
        if model._meta.app_label == 'users':
            return 'users_db'
        elif model._meta.app_label == 'shifting':
            return 'shifting_db'
        elif model._meta.app_label == 'analytics':
            return 'analytics_db'
        return 'default'
    
    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations if both models are in the same database."""
        db_set = {'users_db', 'shifting_db', 'analytics_db', 'default'}
        
        if obj1._state.db in db_set and obj2._state.db in db_set:
            return True
        return None
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Make sure each app only appears in its database."""
        if app_label == 'users':
            return db == 'users_db'
        elif app_label == 'shifting':
            return db == 'shifting_db'
        elif app_label == 'analytics':
            return db == 'analytics_db'
        elif app_label in ['admin', 'auth', 'contenttypes', 'sessions']:
            return db == 'default'
        return None
    
    