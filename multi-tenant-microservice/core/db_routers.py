class TenantRouter:
    """
    Database router for multi-tenancy
    """
    
    def db_for_read(self, model, **hints):
        # Django built-in apps always use default database
        if model._meta.app_label in ['admin', 'auth', 'contenttypes', 'sessions', 'authtoken']:
            return 'default'
        # Users service uses default database
        elif model._meta.app_label == 'users_service':
            return 'default'
        # Shipping service uses tenant databases
        elif model._meta.app_label == 'shipping_service':
            # Get tenant from hints or default to tenant_1
            from django.db import connections
            tenant_id = getattr(connections['default'], 'tenant_id', '1')
            return f'tenant_{tenant_id}'
        return 'default'
    
    def db_for_write(self, model, **hints):
        return self.db_for_read(model, **hints)
    
    def allow_relation(self, obj1, obj2, **hints):
        # Allow all relations
        return True
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Determine which migrations should be run on which databases.
        """
        # Django built-in apps ONLY in default database
        if app_label in ['admin', 'auth', 'contenttypes', 'sessions', 'authtoken']:
            return db == 'default'
        # users_service ONLY in default database
        elif app_label == 'users_service':
            return db == 'default'
        # shipping_service in ALL tenant databases
        elif app_label == 'shipping_service':
            return db in ['tenant_1', 'tenant_2']
        return None