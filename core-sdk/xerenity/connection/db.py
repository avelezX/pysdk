from supabase import create_client, Client
from supabase.client import ClientOptions


class Connection:

    def __init__(self):
        url: str = "https://tvpehjbqxpiswkqszwwv.supabase.co"
        key: str = "sb_publishable_j8Qlvv34vDqMAC01fQE8GA_-DmBfreq"
        self.supabase: Client = create_client(
            url, key,
            options=ClientOptions(
                auto_refresh_token=False,
                postgrest_client_timeout=40,
                storage_client_timeout=40,
                schema="xerenity",
            ))

    def login(self, username, password):
        """

        Inicia sesion con el servidor de xerenity

        :param username: Usuario
        :param password: contrasena
        :return:
        """
        try:
            data = self.supabase.auth.sign_in_with_password(
                {
                    "email": username,
                    "password": password}
            )
            return data

        except Exception as er:
            return str(er)

    def get_all_series(self, grupo: str = None, sub_group: str = None, fuente: str = None, activo: bool = None, query: str = None, frequency: str = None, es_compartimento: bool = None, apertura: str = None):
        """
        Retorna el catálogo de series disponibles en Xerenity.

        Args:
            grupo: Filtra por grupo (ej. 'IBR-SWAP', 'Tasas de Interés').
            sub_group: Filtra por sub-grupo dentro del grupo.
            fuente: Filtra por fuente de datos (ej. 'Banrep', 'BTG Pactual').
            activo: Si True, retorna solo series con datos en los últimos 90 días.
            query: Búsqueda por texto en display_name (insensible a mayúsculas).
            frequency: Filtra por frecuencia: 'D' (diaria), 'W' (semanal), 'M' (mensual),
                       'Q' (trimestral), 'A' (anual), 'I' (irregular).
            es_compartimento: (Solo FIC) Si True, retorna solo sub-compartimentos de FCP.
                              Si False, retorna solo fondos principales.
            apertura: (Solo FIC) Filtra por tipo de apertura:
                      'Abierto', 'Abierto con pacto', 'Abierto sin pacto', 'Cerrado'.

        Returns:
            list[dict]: Lista de series con campos: ticker, display_name, description,
                        grupo, sub_group, fuente, entidad, activo, source_name,
                        frequency (D/W/M/Q/A/I), unit (% EA, COP/USD, Índice, etc.),
                        es_compartimento (bool|None), apertura (str|None).
        """
        try:
            q = self.supabase.from_('search_mv').select(
                'source_name,grupo,sub_group,description,display_name,ticker,fuente,entidad,activo,frequency,unit,es_compartimento,apertura'
            )
            if grupo:
                q = q.eq('grupo', grupo)
            if sub_group:
                q = q.eq('sub_group', sub_group)
            if fuente:
                q = q.eq('fuente', fuente)
            if activo is not None:
                q = q.eq('activo', activo)
            if query:
                q = q.ilike('display_name', f'%{query}%')
            if frequency:
                q = q.eq('frequency', frequency)
            if es_compartimento is not None:
                q = q.eq('es_compartimento', es_compartimento)
            if apertura is not None:
                q = q.eq('apertura', apertura)
            return q.execute().data
        except Exception as er:
            return str(er)

    def read_serie(self, ticker: str):
        """
        Retorna los valores históricos de una serie dado su ticker (MD5 hash).

        Args:
            ticker: Hash MD5 del identificador de la serie (obtenido de portfolio()).

        Returns:
            list[dict]: Lista de puntos [{"time": "YYYY-MM-DD", "value": float}].
        """
        try:
            data = self.supabase.rpc('search', {"ticket": ticker}).execute().data
            if 'data' in data:
                return data['data']
            return data
        except Exception as er:
            return str(er)

    def read_serie_by_slug(self, slug: str):
        """
        Retorna los valores históricos de una serie dado su slug (source_name legible).

        Args:
            slug: Identificador legible de la serie (campo source_name en portfolio()).
                  Ejemplos: 'ibr_3m', 'USD:COP', 'SOFR', 'NOMINAL_120', 'ibr_implicita_1m'.

        Returns:
            list[dict]: Lista de puntos [{"time": "YYYY-MM-DD", "value": float}].
        """
        try:
            data = self.supabase.rpc('search_by_slug', {"slug": slug}).execute().data
            if 'data' in data:
                return data['data']
            return data
        except Exception as er:
            return str(er)

    def get_groups(self) -> list:
        """
        Retorna la lista de grupos disponibles en Xerenity, consultada desde la base de datos.

        Returns:
            list[str]: Lista ordenada de grupos únicos.
        """
        try:
            data = self.supabase.from_('search_mv').select('grupo').execute().data
            return sorted(set(row['grupo'] for row in data if row['grupo']))
        except Exception as er:
            return str(er)

    def get_entities(self, grupo: str = None) -> list:
        """
        Retorna la lista única de entidades (gestoras) disponibles.

        Args:
            grupo: Filtra por grupo (ej. 'FIC'). Si None, retorna todas las entidades.

        Returns:
            list[str]: Lista ordenada de entidades únicas.
        """
        try:
            q = self.supabase.from_('search_mv').select('entidad')
            if grupo:
                q = q.eq('grupo', grupo)
            q = q.not_.is_('entidad', 'null')
            data = q.execute().data
            return sorted(set(row['entidad'] for row in data if row['entidad']))
        except Exception as er:
            return str(er)

    def call_rpc(self, rpc_name, rpc_body: dict):
        return self.supabase.rpc(rpc_name, rpc_body).execute().data

    def list_loans(self, bank_names: list = None):
        """
        Lee la lista entera de creditos en xerenity
        :return:
        """
        try:

            loans_list = self.call_rpc('get_loans', {
                "bank_name_filter": bank_names
            })

            return loans_list

        except Exception as er:
            return str(er)

    def create_loan(self,
                    start_date: str,
                    bank: str,
                    number_of_payments: int,
                    original_balance: float,
                    periodicity: str,
                    interest_rate: float,
                    type: str,
                    days_count: str = None,
                    grace_type: str = None,
                    grace_period: int = None,
                    min_period_rate: float = None,
                    loan_identifier: str = None,
                    ):

        try:

            return self.supabase.rpc('create_credit', {
                "start_date": start_date,
                "bank": bank,
                "number_of_payments": number_of_payments,
                "original_balance": original_balance,
                "periodicity": periodicity,
                "interest_rate": interest_rate,
                "type": type,
                "days_count": days_count,
                "grace_type": grace_type,
                "grace_period": grace_period,
                "min_period_rate": min_period_rate,
                "loan_identifier": loan_identifier,
            }).execute().data

        except Exception as er:
            return str(er)
