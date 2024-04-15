mod results {
    pub enum GetResult {
        Found(T),
        NotFound,
    }

    pub enum HeadResult {
        Found,
        NotFound,
    }

    pub enum PutResult {
        Created,
        Updated,
    }

    pub enum DeleteResult {
        Deleted,
        NotFound,
    }
}
