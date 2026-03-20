class Series:

    def __init__(self, connection):
        self.sup = connection

    def groups(self) -> list:
        """
        Retorna la lista de grupos disponibles en Xerenity, consultada en tiempo real.

        Returns:
            list[str]: Lista ordenada de grupos únicos (25 grupos, ~4,600 series).

        Example:
            >>> x.series.groups()
            ['Agregados Crediticios', 'Agregados Monetarios', 'COLTES', 'Construccion',
             'Cuentas Nacionales', 'Divisas', 'Empleo y Salarios', 'FIC', ...]
        """
        return self.sup.get_groups()

    def portfolio(self, grupo: str = None, sub_group: str = None, fuente: str = None, activo: bool = None, frequency: str = None, es_compartimento: bool = None, apertura: str = None, as_dataframe: bool = False):
        """
        Retorna el catálogo de series disponibles, con filtros opcionales.

        Args:
            grupo: Filtra por grupo primario. Ver x.series.groups() para opciones.
                   Ej: 'IBR-SWAP', 'Tasas de Interés', 'FIC', 'COLTES'.
            sub_group: Filtra por sub-grupo dentro del grupo.
                   Ej: 'IBR', 'UST Nominal', 'FIC De Mercado Monetario'.
            fuente: Filtra por fuente de datos.
                   Ej: 'BanRep', 'BTG Pactual', 'NY Fed'.
            activo: Si True, retorna solo series con datos en los últimos 90 días.
            frequency: Filtra por frecuencia de publicación.
                   'D' = diaria, 'W' = semanal, 'M' = mensual,
                   'Q' = trimestral, 'A' = anual, 'I' = irregular.
            es_compartimento: (Solo FIC) Filtra sub-compartimentos de Fondos de Capital
                   Privado. True = solo compartimentos, False = solo fondos principales.
            apertura: (Solo FIC) Filtra por tipo de apertura:
                   'Abierto'            — abierto sin especificar pacto.
                   'Abierto con pacto'  — abierto con pacto de permanencia.
                   'Abierto sin pacto'  — abierto sin pacto de permanencia.
                   'Cerrado'            — fondo cerrado.
            as_dataframe: Si True, retorna un DataFrame de pandas en lugar de list[dict].
                   Requiere pandas instalado.

        Returns:
            list[dict] o DataFrame: Lista de series. Cada elemento contiene:
                - ticker (str): Identificador único (legacy).
                - source_name (str): Slug legible para usar en search(slug=...).
                - display_name (str): Nombre legible.
                - description (str): Descripción detallada.
                - grupo (str): Grupo primario.
                - sub_group (str): Sub-grupo.
                - fuente (str): Fuente del dato.
                - frequency (str): Frecuencia — D/W/M/Q/A/I.
                - unit (str): Unidad del valor (% EA, COP/USD, Índice, etc.).
                - entidad (str|None): Gestora administradora (solo FIC).
                - activo (bool|None): True si tiene datos en los últimos 90 días.
                - es_compartimento (bool|None): True si es sub-compartimento FCP (solo FIC).
                - apertura (str|None): Tipo de apertura del fondo (solo FIC).

        Examples:
            >>> x.series.portfolio()
            >>> x.series.portfolio(grupo="IBR-SWAP")
            >>> x.series.portfolio(grupo="FIC", sub_group="FIC De Mercado Monetario")
            >>> x.series.portfolio(grupo="Tasas de Interés", activo=True)
            >>> x.series.portfolio(frequency="M")
            >>> x.series.portfolio(grupo="FIC", apertura="Abierto con pacto")
            >>> x.series.portfolio(grupo="FIC", apertura="Cerrado")
            >>> x.series.portfolio(grupo="FIC", es_compartimento=False, activo=True)
            >>> x.series.portfolio(grupo="FIC", es_compartimento=True)  # solo FCP compartimentos
            >>> x.series.portfolio(grupo="FIC", as_dataframe=True)
        """
        result = self.sup.get_all_series(grupo=grupo, sub_group=sub_group, fuente=fuente, activo=activo, frequency=frequency, es_compartimento=es_compartimento, apertura=apertura)
        if as_dataframe:
            try:
                import pandas as pd
            except ImportError:
                raise ImportError("pandas es requerido para as_dataframe=True. Instala con: pip install pandas")
            return pd.DataFrame(result)
        return result

    def search_by_name(self, query: str) -> list:
        """
        Busca series por nombre (insensible a mayúsculas/minúsculas).

        Args:
            query: Texto a buscar en el nombre de la serie.

        Returns:
            list[dict]: Series cuyo display_name contiene el texto buscado.

        Examples:
            >>> x.series.search_by_name("IBR")
            >>> x.series.search_by_name("desempleo")
            >>> x.series.search_by_name("SOFR")
        """
        return self.sup.get_all_series(query=query)

    def search(self, ticker: str = None, slug: str = None, desde: str = None, hasta: str = None) -> list:
        """
        Retorna los valores históricos de una serie.

        Acepta dos formas de identificar la serie:
          - ticker: el hash MD5 (campo 'ticker' en portfolio()). Compatible con versiones anteriores.
          - slug:   el identificador legible (campo 'source_name' en portfolio()). Recomendado.

        Args:
            ticker: Hash MD5 de la serie. Ej: '3d9f4cdbc81a0e04d61b6c9601f3a049'.
            slug:   Source name legible. Ej: 'ibr_3m', 'USD:COP', 'SOFR', 'NOMINAL_120'.
            desde:  Fecha inicio (inclusive), formato 'YYYY-MM-DD'. Ej: '2024-01-01'.
            hasta:  Fecha fin (inclusive), formato 'YYYY-MM-DD'. Ej: '2024-12-31'.

        Returns:
            list[dict]: Lista de puntos [{"time": "YYYY-MM-DD", "value": float}].

        Examples:
            >>> x.series.search(slug="ibr_3m")
            >>> x.series.search(slug="USD:COP", desde="2024-01-01")
            >>> x.series.search(slug="SOFR", desde="2023-01-01", hasta="2023-12-31")
            >>> x.series.search(ticker="3d9f4cdbc81a0e04d61b6c9601f3a049")

            >>> # Flujo completo
            >>> resultados = x.series.portfolio(grupo="Política Monetaria")
            >>> data = x.series.search(slug=resultados[0]["source_name"])
        """
        if slug is not None:
            data = self.sup.read_serie_by_slug(slug=slug)
        elif ticker is not None:
            data = self.sup.read_serie(ticker=ticker)
        else:
            raise ValueError("Debes pasar 'ticker' o 'slug'. Usa portfolio() para obtener los identificadores disponibles.")

        if isinstance(data, list) and (desde or hasta):
            if desde:
                data = [p for p in data if p['time'] >= desde]
            if hasta:
                data = [p for p in data if p['time'] <= hasta]

        return data

    def search_multiple(self, slugs: list, desde: str = None, hasta: str = None):
        """
        Descarga varias series a la vez y las combina en un DataFrame.

        Requiere pandas instalado: pip install pandas

        Args:
            slugs:  Lista de source_name (slugs) a descargar.
                    Ej: ['ibr_3m', 'ibr_6m', 'USD:COP']
            desde:  Fecha inicio (inclusive), formato 'YYYY-MM-DD'. Ej: '2024-01-01'.
            hasta:  Fecha fin (inclusive), formato 'YYYY-MM-DD'. Ej: '2024-12-31'.

        Returns:
            pd.DataFrame: Índice = fecha (datetime), columnas = slugs.
                          NaN donde no hay dato para esa fecha.

        Examples:
            >>> df = x.series.search_multiple(['ibr_3m', 'ibr_6m', 'ibr_1y'])
            >>> df = x.series.search_multiple(['USD:COP', 'SOFR'], desde="2024-01-01")
            >>> df.plot()
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas es requerido para search_multiple(). Instala con: pip install pandas")

        frames = []
        for slug in slugs:
            data = self.search(slug=slug, desde=desde, hasta=hasta)
            if isinstance(data, list) and data:
                df = pd.DataFrame(data).rename(columns={'value': slug})
                df['time'] = pd.to_datetime(df['time'])
                df = df.set_index('time')
                frames.append(df)

        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, axis=1).sort_index()

    def entities(self, grupo: str = None) -> list:
        """
        Retorna la lista de entidades (gestoras) únicas disponibles.

        Principalmente útil para el grupo 'FIC', donde cada fondo tiene una gestora.

        Args:
            grupo: Filtra por grupo. Ej: 'FIC'. Si None, retorna todas las entidades.

        Returns:
            list[str]: Lista ordenada de entidades únicas.

        Examples:
            >>> x.series.entities(grupo="FIC")
            ['Alianza Valores', 'Bancolombia', 'BTG Pactual', ...]
            >>> x.series.entities()   # todas las entidades
        """
        return self.sup.get_entities(grupo=grupo)
